#!/usr/bin/env python3
# Copyright Materialize, Inc. All rights reserved.
#
# Use of this software is governed by the Business Source License
# included in the LICENSE file at the root of this repository.
#
# As of the Change Date specified in that file, in accordance with
# the Business Source License, use of this software will be governed
# by the Apache License, Version 2.0.

"""summarize_topics

Basic script to print messages count and number of bytes within a Kafka topic
"""

import argparse
import time

import kafka


def summarize_topic(args, topic):
    """Read messages from a topic and print basic information about the topic."""

    consumer = kafka.KafkaConsumer(
        topic,
        auto_offset_reset="earliest",
        consumer_timeout_ms=1000,
        bootstrap_servers=[f"{args.kafkahost}:{args.port}"],
        enable_auto_commit=True,
    )

    start = time.time()

    num_messages = 0
    key_bytes = 0
    value_bytes = 0
    for message in consumer:
        num_messages += 1
        key_bytes += len(message.key) if message.key else 0
        value_bytes += len(message.value) if message.value else 0

    seconds_elapsed = time.time() - start
    print(f"{topic},{num_messages},{key_bytes},{value_bytes},{seconds_elapsed:.1f}s")


def summarize_topics(args):
    """Read messages from topics matching prefix and print basic information about the topic."""

    consumer = kafka.KafkaConsumer(bootstrap_servers=[f"{args.kafkahost}:{args.port}"])
    topics = sorted([t for t in consumer.topics() if t.startswith(args.topic_prefix)])

    print("Topic,NumMessages,KeyBytes,ValueBytes,PythonConsumerTimeElapsed")
    for topic in topics:
        summarize_topic(args, topic)


def main():
    """Parse arguments and print topic summaries."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-k",
        "--kafkahost",
        help="Filter topics by prefix string",
        type=str,
        default="localhost",
    )
    parser.add_argument(
        "-p", "--port", help="Filter topics by prefix string", type=int, default=9092
    )
    parser.add_argument(
        "-t",
        "--topic-prefix",
        help="Filter topics by prefix string",
        type=str,
        default="debezium.tpcch",
    )

    args = parser.parse_args()
    summarize_topics(args)


if __name__ == "__main__":
    main()
