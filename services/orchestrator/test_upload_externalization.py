import base64
import json

import app


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.queue = []

    def set(self, key, value, ex=None):
        self.values[key] = value
        return True

    def rpush(self, key, value):
        self.queue.append((key, value))
        return len(self.queue)


def test_submit_externalizes_inline_video(monkeypatch):
    s3 = FakeS3()
    redis = FakeRedis()
    monkeypatch.setattr(app, "s3_client", s3)
    monkeypatch.setattr(app, "redis_client", redis)
    monkeypatch.setattr(app, "OBJECT_STORAGE_BUCKET", "drift-artifacts")

    encoded = base64.b64encode(b"video-bytes").decode()
    result = app.submit_run(app.MissionSubmission(video_base64=encoded, video_file_name="clip.mp4"))

    assert result["status"] == "queued"
    assert len(s3.objects) == 1
    queued = json.loads(redis.queue[0][1])
    assert "video_base64" not in queued
    assert queued["video_uri"].startswith("s3://drift-artifacts/missions/")
    assert redis.values[f"job:{result['run_id']}"]
    assert encoded not in redis.values[f"job:{result['run_id']}"]
