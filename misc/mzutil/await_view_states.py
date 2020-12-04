#!/usr/bin/env python3
# Copyright Materialize, Inc. All rights reserved.
#
# Use of this software is governed by the Business Source License
# included in the LICENSE file at the root of this repository.
#
# As of the Change Date specified in that file, in accordance with
# the Business Source License, use of this software will be governed
# by the Apache License, Version 2.0.

"""await_view_states

Script to query all materialized views in a Materialize database and wait until each view matches
the exact output as captured in the snapshot files.

Prints timing information to indicate how long each view took to reach the desired state.
"""

import argparse
import glob
import io
import os
import time

import psycopg2
import psycopg2.errors


def view_names(conn):
    """Return a generator containing all view names in Materialize."""
    with conn.cursor() as cursor:
        cursor.execute("SHOW VIEWS")
        for row in cursor:
            yield row[0]


def view_matches(cursor, view, expected):
    """Return True if a SELECT from the VIEW matches the expected string."""
    stream = io.StringIO()
    try:
        cursor.copy_expert(f"COPY (SELECT * FROM {view}) TO STDOUT", stream)
    except psycopg2.errors.InternalError_:
        # The view is not yet ready to be queried
        return False
    return stream.getvalue() == expected


def await_materialize_views(args):
    """Record the current table status of all views installed in Materialize."""

    start_time = time.time()

    def file_contents(fname):
        with open(fname, "r") as fd:
            return fd.read()

    # Create a dictionary mapping view names (as calculated from the filename) to expected contents
    view_snapshots = {
        os.path.splitext(os.path.basename(fname))[0]: file_contents(fname)
        for fname in glob.glob(os.path.join(args.snapshot_dir, "*.sql"))
    }

    with psycopg2.connect(f"postgresql://{args.host}:{args.port}/materialize") as conn:
        installed_views = set(view_names(conn))

    # Verify that we have snapshots for all views installed
    captured_views = set(view_snapshots.keys())
    if not captured_views.issuperset(installed_views):
        missing_views = installed_views.difference(captured_views)
        print(f"ERROR: Missing final state for views: {missing_views}")
        sys.exit(1)

    print("Recording time required until each view matches its snapshot")

    pending_views = installed_views
    with psycopg2.connect(f"postgresql://{args.host}:{args.port}/materialize") as conn:
        while pending_views:
            views_to_remove = []
            for view in pending_views:
                with conn.cursor() as cursor:
                    if view_matches(cursor, view, view_snapshots[view]):
                        time_taken = time.time() - start_time
                        print(f"{time_taken:>6.1f}s: {view}")
                        views_to_remove.append(view)

            for view in views_to_remove:
                pending_views.remove(view)

            time.sleep(0.1)


def main():
    """Parse arguments and snapshot materialized views."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", help="Materialize hostname", default="materialized", type=str
    )
    parser.add_argument(
        "-p", "--port", help="Materialize port number", default=6875, type=int
    )

    parser.add_argument(
        "-d",
        "--snapshot-dir",
        help="Directory containing view snapshots",
        type=str,
        default="/snapshot",
    )

    args = parser.parse_args()
    await_materialize_views(args)


if __name__ == "__main__":
    main()
