"""
tests/test_feed.py — Mixtape

Tests for the "Friends Listening Now" recency window (Issue #2).
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent, friendships
from services.feed_service import get_friends_listening_now, get_activity_feed


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def social(app):
    """A user with one friend and a song the friend can listen to."""
    with app.app_context():
        me = User(username="me", email="me@example.com")
        friend = User(username="friend", email="friend@example.com")
        db.session.add_all([me, friend])
        db.session.flush()

        db.session.execute(
            friendships.insert().values(user_id=me.id, friend_id=friend.id)
        )

        song = Song(title="Neon City", artist="Synthwave", shared_by=me.id)
        db.session.add(song)
        db.session.flush()
        db.session.commit()
        yield {"me": me, "friend": friend, "song": song}


def _listen(friend_id, song_id, ago):
    db.session.add(ListeningEvent(
        user_id=friend_id, song_id=song_id,
        listened_at=datetime.now(timezone.utc) - ago,
    ))
    db.session.commit()


def test_recent_listen_appears(app, social):
    """A friend who listened a few minutes ago shows up in Listening Now."""
    with app.app_context():
        _listen(social["friend"].id, social["song"].id, timedelta(minutes=5))
        feed = get_friends_listening_now(social["me"].id)
        assert len(feed) == 1
        assert feed[0]["friend"]["username"] == "friend"


def test_yesterday_listen_does_not_appear(app, social):
    """A friend who last listened 20h ago (yesterday) must NOT appear — Issue #2."""
    with app.app_context():
        _listen(social["friend"].id, social["song"].id, timedelta(hours=20))
        feed = get_friends_listening_now(social["me"].id)
        assert feed == []


def test_activity_feed_still_shows_older_events(app, social):
    """The (non-recency-filtered) activity feed still surfaces older listens."""
    with app.app_context():
        _listen(social["friend"].id, social["song"].id, timedelta(hours=20))
        feed = get_activity_feed(social["me"].id)
        assert len(feed) == 1
