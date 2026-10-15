from collections.abc import Mapping, Sequence, Set

from sybarite_feed.channel import ChannelVideo

MAX_ATTEMPTS = 3


def select_batch(
    videos: Sequence[ChannelVideo],
    done: Set[str],
    failures: Mapping[str, int],
    min_duration: int,
    limit: int,
) -> list[ChannelVideo]:
    batch = []
    for video in videos:
        if len(batch) >= limit:
            break
        if video.id in done or failures.get(video.id, 0) >= MAX_ATTEMPTS:
            continue
        # no duration means a premiere that is not published yet; it gets picked up later
        if video.duration is None or video.duration < min_duration:
            continue
        batch.append(video)
    return batch
