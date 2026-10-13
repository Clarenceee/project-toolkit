import json
import os


def mock_process(payload: str) -> str:
    event = json.loads(payload)
    if not isinstance(event, dict):
        raise ValueError("Kafka message must be a JSON object")
    event["processed_by"] = "flink"
    return json.dumps(event, separators=(",", ":"), sort_keys=True)


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def main() -> None:
    from pyflink.common import Types, WatermarkStrategy
    from pyflink.common.serialization import SimpleStringSchema
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.datastream.connectors.base import DeliveryGuarantee
    from pyflink.datastream.connectors.kafka import (
        KafkaOffsetResetStrategy,
        KafkaOffsetsInitializer,
        KafkaRecordSerializationSchema,
        KafkaSink,
        KafkaSource,
    )

    job_name = os.getenv("FLINK_JOB_NAME", "flink-example")
    bootstrap_servers = required("KAFKA_BOOTSTRAP_SERVERS")
    source_topic = required("KAFKA_SOURCE_TOPIC")
    sink_topic = required("KAFKA_SINK_TOPIC")
    group_id = os.getenv("KAFKA_GROUP_ID") or job_name
    parallelism = positive_int("FLINK_PARALLELISM", 1)

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(parallelism)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_topics(source_topic)
        .set_group_id(group_id)
        .set_starting_offsets(
            KafkaOffsetsInitializer.committed_offsets(KafkaOffsetResetStrategy.EARLIEST)
        )
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(sink_topic)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .build()
    )

    (
        env.from_source(source, WatermarkStrategy.no_watermarks(), "kafka-source")
        .uid("kafka-source")
        .map(mock_process, output_type=Types.STRING())
        .name("mock-process-events")
        .uid("mock-process-events")
        .sink_to(sink)
        .name("kafka-sink")
        .uid("kafka-sink")
    )

    env.execute(job_name)


if __name__ == "__main__":
    main()
