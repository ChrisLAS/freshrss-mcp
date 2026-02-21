"""Tests for models.py — data model serialization and construction."""

from freshrss_mcp.models import Article, Feed


class TestArticle:
    def test_construction(self):
        article = Article(
            id=123,
            title="Test Article",
            summary="A brief summary",
            url="https://example.com/article",
            published=1700000000,
            feed_name="Tech News",
            is_read=False,
            is_starred=True,
        )
        assert article.id == 123
        assert article.title == "Test Article"
        assert article.is_starred is True
        assert article.is_read is False

    def test_to_dict_contains_all_fields(self):
        article = Article(
            id=1,
            title="T",
            summary="S",
            url="U",
            published=0,
            feed_name="F",
            is_read=True,
            is_starred=False,
        )
        d = article.to_dict()
        assert set(d.keys()) == {
            "id",
            "title",
            "summary",
            "url",
            "published",
            "feed_name",
            "is_read",
            "is_starred",
        }

    def test_to_dict_values(self):
        article = Article(
            id=42,
            title="Hello",
            summary="World",
            url="https://x.com",
            published=999,
            feed_name="Feed",
            is_read=False,
            is_starred=True,
        )
        d = article.to_dict()
        assert d["id"] == 42
        assert d["title"] == "Hello"
        assert d["published"] == 999
        assert d["is_starred"] is True

    def test_empty_summary(self):
        article = Article(
            id=1,
            title="T",
            summary="",
            url="",
            published=0,
            feed_name="F",
            is_read=False,
            is_starred=False,
        )
        assert article.to_dict()["summary"] == ""


class TestFeed:
    def test_construction_with_defaults(self):
        feed = Feed(id=10, name="My Feed", url="https://example.com/feed")
        assert feed.unread_count == 0

    def test_construction_with_unread(self):
        feed = Feed(id=10, name="My Feed", url="https://example.com/feed", unread_count=42)
        assert feed.unread_count == 42

    def test_to_dict(self):
        feed = Feed(id=5, name="News", url="https://news.com/rss", unread_count=3)
        d = feed.to_dict()
        assert d == {
            "id": 5,
            "name": "News",
            "url": "https://news.com/rss",
            "unread_count": 3,
        }

    def test_mutable_unread_count(self):
        """Tools mutate unread_count after construction — verify this works."""
        feed = Feed(id=1, name="F", url="U")
        feed.unread_count = 99
        assert feed.to_dict()["unread_count"] == 99
