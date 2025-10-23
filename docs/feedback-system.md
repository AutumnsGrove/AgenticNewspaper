# Feedback & Learning System

**Version:** 2.0
**Date:** October 23, 2025
**Purpose:** Documents the user feedback tracking and personalization learning system

---

## Overview

The Intelligent News Aggregator includes a feedback and learning system that adapts to your reading patterns over time. The system operates in two phases:

1. **Phase 1-4 (Passive Tracking):** Automatically monitors what you read
2. **Phase 5+ (Active Feedback + Learning):** Allows manual ratings and learns preferences

---

## Phase 1-4: Passive Tracking

### What Gets Tracked

```python
@dataclass
class PassiveReading:
    """Automatically tracked reading data"""
    digest_id: str           # Which digest
    article_id: str          # Which article
    timestamp: datetime      # When accessed
    file_opened: bool        # Did user open the digest file?
    time_spent_seconds: int  # How long spent reading (inferred)
    scroll_depth: float      # How far through article (0.0-1.0, if web UI)
```

### How It Works

#### File-Based Tracking (Phase 1-3)

```python
# src/feedback/tracker.py

import os
from pathlib import Path
from datetime import datetime

class PassiveTracker:
    """Track reading patterns without explicit user input"""

    def __init__(self, db_path: str = "data/feedback.db"):
        self.db = sqlite3.connect(db_path)
        self.setup_tables()

    def track_digest_created(self, digest_id: str):
        """Log when a digest is generated"""
        self.db.execute(
            """INSERT INTO digests (id, created_at, accessed_at)
               VALUES (?, ?, NULL)""",
            (digest_id, datetime.now())
        )
        self.db.commit()

    def track_digest_accessed(self, digest_id: str):
        """Log when digest file is opened"""
        self.db.execute(
            """UPDATE digests SET accessed_at = ?
               WHERE id = ?""",
            (datetime.now(), digest_id)
        )
        self.db.commit()

    def infer_reading_time(self, file_path: str) -> int:
        """
        Infer reading time based on file access patterns
        Uses OS filesystem metadata
        """
        stat = os.stat(file_path)

        # Access time - modified time = time spent reading
        accessed = datetime.fromtimestamp(stat.st_atime)
        modified = datetime.fromtimestamp(stat.st_mtime)

        # If file accessed significantly after creation, user probably read it
        time_diff = (accessed - modified).total_seconds()

        # Heuristic: files accessed >30s after creation were likely read
        if time_diff > 30:
            return int(time_diff)
        else:
            return 0  # Likely just generated, not read

    def get_read_articles(self, days: int = 7) -> List[str]:
        """
        Get list of article IDs that were likely read
        based on file access patterns
        """
        # Query digests accessed in last N days
        cursor = self.db.execute(
            """SELECT id, created_at, accessed_at
               FROM digests
               WHERE accessed_at IS NOT NULL
               AND accessed_at >= datetime('now', '-' || ? || ' days')""",
            (days,)
        )

        read_digests = cursor.fetchall()

        # For each digest, infer which articles were read
        # (All articles in an accessed digest are assumed read)
        read_articles = []
        for digest_id, created, accessed in read_digests:
            articles = self.get_articles_in_digest(digest_id)
            read_articles.extend(articles)

        return read_articles
```

#### Web UI Tracking (Phase 4+)

```python
# web/app.py

from flask import Flask, request, jsonify

app = Flask(__name__)
tracker = PassiveTracker()

@app.route("/digest/<digest_id>")
def view_digest(digest_id):
    """Serve digest and track access"""

    # Log access
    tracker.track_digest_accessed(digest_id)

    # Serve digest
    digest = load_digest(digest_id)
    return render_template("digest.html", digest=digest)

@app.route("/api/track/scroll", methods=["POST"])
def track_scroll():
    """Track how far user scrolled through article"""

    data = request.json
    tracker.track_scroll_depth(
        article_id=data["article_id"],
        scroll_depth=data["scroll_depth"]  # 0.0 - 1.0
    )

    return jsonify({"status": "ok"})

@app.route("/api/track/time", methods=["POST"])
def track_time():
    """Track time spent on article"""

    data = request.json
    tracker.track_time_spent(
        article_id=data["article_id"],
        time_seconds=data["time_seconds"]
    )

    return jsonify({"status": "ok"})
```

### Basic Insights from Passive Data

```python
# src/feedback/insights.py

class PassiveInsights:
    """Generate insights from passive tracking data"""

    def __init__(self, tracker: PassiveTracker):
        self.tracker = tracker

    def get_topic_read_rates(self, days: int = 30) -> Dict[str, float]:
        """
        Calculate what % of articles in each topic get read
        """
        read_articles = set(self.tracker.get_read_articles(days))
        all_articles = self.tracker.get_all_articles(days)

        topic_stats = {}
        for topic in TOPICS:
            topic_articles = [a for a in all_articles if a.topic == topic]
            topic_read = [a for a in topic_articles if a.id in read_articles]

            read_rate = len(topic_read) / len(topic_articles) if topic_articles else 0
            topic_stats[topic] = read_rate

        return topic_stats

    def get_source_read_rates(self, days: int = 30) -> Dict[str, float]:
        """
        Calculate what % of articles from each source get read
        """
        read_articles = set(self.tracker.get_read_articles(days))
        all_articles = self.tracker.get_all_articles(days)

        source_stats = {}
        for source in SOURCES:
            source_articles = [a for a in all_articles if a.source == source]
            source_read = [a for a in source_articles if a.id in read_articles]

            read_rate = len(source_read) / len(source_articles) if source_articles else 0
            source_stats[source] = read_rate

        return source_stats

    def get_optimal_article_count(self, days: int = 30) -> int:
        """
        Infer optimal article count based on read rates
        """
        digests = self.tracker.get_recent_digests(days)

        # Calculate read rate for each digest
        digest_stats = []
        for digest in digests:
            total = len(digest.articles)
            read = len([a for a in digest.articles if self.tracker.was_read(a.id)])
            read_rate = read / total if total > 0 else 0

            digest_stats.append({
                "total_articles": total,
                "read_articles": read,
                "read_rate": read_rate
            })

        # Find the article count where read rate is highest
        avg_read_rate_by_count = {}
        for stat in digest_stats:
            count = stat["total_articles"]
            rate = stat["read_rate"]

            if count not in avg_read_rate_by_count:
                avg_read_rate_by_count[count] = []
            avg_read_rate_by_count[count].append(rate)

        # Average read rates for each article count
        for count, rates in avg_read_rate_by_count.items():
            avg_read_rate_by_count[count] = sum(rates) / len(rates)

        # Return count with highest read rate
        optimal = max(avg_read_rate_by_count.items(), key=lambda x: x[1])
        return optimal[0]

    def generate_report(self, days: int = 30) -> str:
        """
        Generate a human-readable insights report
        """
        topic_rates = self.get_topic_read_rates(days)
        source_rates = self.get_source_read_rates(days)
        optimal_count = self.get_optimal_article_count(days)

        report = f"""
# Passive Tracking Insights (Last {days} Days)

## Topic Read Rates
"""
        for topic, rate in sorted(topic_rates.items(), key=lambda x: x[1], reverse=True):
            report += f"- {topic}: {rate*100:.1f}% read\n"

        report += "\n## Source Read Rates\n"
        for source, rate in sorted(source_rates.items(), key=lambda x: x[1], reverse=True):
            report += f"- {source}: {rate*100:.1f}% read\n"

        report += f"\n## Optimal Article Count\n"
        report += f"Based on your reading patterns, {optimal_count} articles per digest seems optimal.\n"

        return report
```

---

## Phase 5+: Active Feedback & Learning

### Active Feedback Interface

#### Web UI Feedback Form

```html
<!-- web/templates/article_feedback.html -->

<div class="article-feedback">
  <h4>Rate this article</h4>

  <div class="rating-section">
    <label>Relevance to your interests:</label>
    <div class="stars">
      <span class="star" data-rating="1">★</span>
      <span class="star" data-rating="2">★</span>
      <span class="star" data-rating="3">★</span>
      <span class="star" data-rating="4">★</span>
      <span class="star" data-rating="5">★</span>
    </div>
    <input type="hidden" id="relevance-rating" name="relevance" />
  </div>

  <div class="rating-section">
    <label>Article quality:</label>
    <div class="stars">
      <span class="star" data-rating="1">★</span>
      <span class="star" data-rating="2">★</span>
      <span class="star" data-rating="3">★</span>
      <span class="star" data-rating="4">★</span>
      <span class="star" data-rating="5">★</span>
    </div>
    <input type="hidden" id="quality-rating" name="quality" />
  </div>

  <div class="rating-section">
    <label>Bias detection accuracy:</label>
    <div class="stars">
      <span class="star" data-rating="1">★</span>
      <span class="star" data-rating="2">★</span>
      <span class="star" data-rating="3">★</span>
      <span class="star" data-rating="4">★</span>
      <span class="star" data-rating="5">★</span>
    </div>
    <input type="hidden" id="bias-accuracy-rating" name="bias_accuracy" />
  </div>

  <div class="quick-actions">
    <button class="btn-favorite" onclick="markFavorite()">⭐ Favorite</button>
    <button class="btn-irrelevant" onclick="markIrrelevant()">❌ Irrelevant</button>
  </div>

  <div class="notes-section">
    <label>Notes (optional):</label>
    <textarea id="feedback-notes" placeholder="Why did you rate it this way?"></textarea>
  </div>

  <button class="btn-submit" onclick="submitFeedback()">Submit Feedback</button>
</div>

<script>
async function submitFeedback() {
  const feedback = {
    article_id: "{{ article.id }}",
    relevance_rating: document.getElementById("relevance-rating").value,
    quality_rating: document.getElementById("quality-rating").value,
    bias_accuracy_rating: document.getElementById("bias-accuracy-rating").value,
    notes: document.getElementById("feedback-notes").value
  };

  await fetch("/api/feedback/submit", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(feedback)
  });

  alert("Feedback submitted! The system will learn from this.");
}
</script>
```

#### Backend Feedback Storage

```python
# web/app.py

@app.route("/api/feedback/submit", methods=["POST"])
def submit_feedback():
    """Store user feedback for learning"""

    data = request.json

    feedback = ActiveFeedback(
        article_id=data["article_id"],
        relevance_rating=int(data["relevance_rating"]),
        quality_rating=int(data["quality_rating"]),
        bias_accuracy_rating=int(data.get("bias_accuracy_rating", 0)),
        marked_favorite=data.get("marked_favorite", False),
        marked_irrelevant=data.get("marked_irrelevant", False),
        notes=data.get("notes", ""),
        timestamp=datetime.now()
    )

    feedback_storage.save(feedback)

    # Trigger learning if enough feedback collected
    if feedback_storage.count() >= MIN_FEEDBACK_SAMPLES:
        learner.update_preferences()

    return jsonify({"status": "ok", "message": "Feedback saved"})
```

### Learning Algorithm

```python
# src/feedback/learner.py

class FeedbackLearner:
    """Learn from user feedback and adjust preferences"""

    def __init__(
        self,
        feedback_db: str = "data/feedback.db",
        preferences_file: str = "config/user_preferences.yaml"
    ):
        self.db = sqlite3.connect(feedback_db)
        self.preferences_file = preferences_file
        self.min_samples = 10  # Minimum feedback before learning

    def update_preferences(self):
        """
        Analyze feedback and update user preferences
        """
        # Get recent feedback (last 30 days)
        feedback = self.get_recent_feedback(days=30)

        if len(feedback) < self.min_samples:
            print(f"Need {self.min_samples - len(feedback)} more feedback samples")
            return

        # Generate insights
        insights = self.analyze_feedback(feedback)

        # Update preferences file
        self.apply_insights(insights)

        print(f"Updated preferences based on {len(feedback)} feedback samples")

    def analyze_feedback(self, feedback: List[ActiveFeedback]) -> LearningInsights:
        """
        Analyze feedback to generate actionable insights
        """
        insights = LearningInsights()

        # 1. Topic preference learning
        insights.topic_weights = self._learn_topic_weights(feedback)

        # 2. Source trust learning
        insights.source_trust = self._learn_source_reliability(feedback)

        # 3. Optimal article count
        insights.optimal_article_count = self._learn_optimal_count(feedback)

        # 4. Quality threshold adjustments
        insights.quality_thresholds = self._learn_thresholds(feedback)

        # 5. Keyword refinements
        insights.keyword_adjustments = self._learn_keywords(feedback)

        return insights

    def _learn_topic_weights(self, feedback: List[ActiveFeedback]) -> Dict[str, int]:
        """
        Adjust topic priorities based on feedback
        """
        topic_stats = {}

        for topic in TOPICS:
            # Get all feedback for this topic
            topic_feedback = [f for f in feedback if f.article_topic == topic]

            if not topic_feedback:
                continue

            # Calculate average relevance rating
            avg_relevance = sum(f.relevance_rating for f in topic_feedback) / len(topic_feedback)

            # Calculate read rate (did user even read articles in this topic?)
            read_rate = sum(1 for f in topic_feedback if f.relevance_rating > 0) / len(topic_feedback)

            # Combined score
            engagement = (avg_relevance / 5.0) * 0.7 + read_rate * 0.3

            # Adjust priority
            current_priority = self.get_current_topic_priority(topic)

            if engagement > 0.8:
                # High engagement - increase priority
                new_priority = min(10, current_priority + 1)
            elif engagement < 0.3:
                # Low engagement - decrease priority
                new_priority = max(1, current_priority - 1)
            else:
                # Moderate engagement - keep current
                new_priority = current_priority

            topic_stats[topic] = new_priority

        return topic_stats

    def _learn_source_reliability(self, feedback: List[ActiveFeedback]) -> Dict[str, float]:
        """
        Learn which sources produce articles user finds valuable
        """
        source_stats = {}

        for source in SOURCES:
            source_feedback = [f for f in feedback if f.article_source == source]

            if not source_feedback:
                continue

            # Average quality rating for this source
            avg_quality = sum(f.quality_rating for f in source_feedback) / len(source_feedback)

            # Average relevance
            avg_relevance = sum(f.relevance_rating for f in source_feedback) / len(source_feedback)

            # Trust score (0-1)
            trust_score = ((avg_quality + avg_relevance) / 2) / 5.0

            source_stats[source] = trust_score

        return source_stats

    def _learn_optimal_count(self, feedback: List[ActiveFeedback]) -> int:
        """
        Determine optimal article count based on reading patterns
        """
        digest_stats = {}

        # Group feedback by digest
        digests = set(f.digest_id for f in feedback)

        for digest_id in digests:
            digest_feedback = [f for f in feedback if f.digest_id == digest_id]

            total_articles = self.get_digest_article_count(digest_id)
            read_articles = sum(1 for f in digest_feedback if f.relevance_rating > 0)

            read_rate = read_articles / total_articles if total_articles > 0 else 0

            digest_stats[total_articles] = digest_stats.get(total_articles, []) + [read_rate]

        # Find article count with highest average read rate
        avg_read_rates = {
            count: sum(rates) / len(rates)
            for count, rates in digest_stats.items()
        }

        optimal_count = max(avg_read_rates.items(), key=lambda x: x[1])[0]

        return optimal_count

    def _learn_thresholds(self, feedback: List[ActiveFeedback]) -> Dict[str, float]:
        """
        Adjust quality thresholds based on user ratings
        """
        # Find articles that user rated highly vs. system scores
        high_user_ratings = [f for f in feedback if f.relevance_rating >= 4]
        low_user_ratings = [f for f in feedback if f.relevance_rating <= 2]

        # What were the system's original scores for these articles?
        high_rated_system_scores = [
            self.get_article_system_score(f.article_id)
            for f in high_user_ratings
        ]

        low_rated_system_scores = [
            self.get_article_system_score(f.article_id)
            for f in low_user_ratings
        ]

        # Calculate new thresholds
        # If system is including low-quality articles, raise threshold
        # If system is excluding good articles, lower threshold

        avg_high_score = sum(high_rated_system_scores) / len(high_rated_system_scores) if high_rated_system_scores else 0.8
        avg_low_score = sum(low_rated_system_scores) / len(low_rated_system_scores) if low_rated_system_scores else 0.6

        # Threshold should be between avg_low and avg_high
        new_threshold = (avg_high_score + avg_low_score) / 2

        return {
            "min_relevance_score": max(0.5, min(0.9, new_threshold)),
            "min_quality_score": max(0.5, min(0.9, new_threshold))
        }

    def _learn_keywords(self, feedback: List[ActiveFeedback]) -> Dict[str, List[str]]:
        """
        Identify keywords in highly-rated vs. low-rated articles
        """
        high_rated = [f for f in feedback if f.relevance_rating >= 4]
        low_rated = [f for f in feedback if f.relevance_rating <= 2]

        # Extract common keywords from high-rated articles
        high_keywords = self._extract_keywords([
            self.get_article_content(f.article_id) for f in high_rated
        ])

        # Extract keywords from low-rated articles
        low_keywords = self._extract_keywords([
            self.get_article_content(f.article_id) for f in low_rated
        ])

        # Keywords that appear in high-rated but not low-rated = add to topics
        # Keywords that appear in low-rated but not high-rated = add to exclusions

        return {
            "add_keywords": list(set(high_keywords) - set(low_keywords)),
            "exclude_keywords": list(set(low_keywords) - set(high_keywords))
        }

    def apply_insights(self, insights: LearningInsights):
        """
        Apply learned insights to user preferences file
        """
        # Load current preferences
        with open(self.preferences_file) as f:
            prefs = yaml.safe_load(f)

        # Update topic priorities
        for topic_name, new_priority in insights.topic_weights.items():
            topic = next((t for t in prefs["topics"] if t["name"] == topic_name), None)
            if topic:
                old_priority = topic["priority"]
                topic["priority"] = new_priority
                print(f"  {topic_name}: priority {old_priority} → {new_priority}")

        # Update quality thresholds
        prefs["quality"]["min_relevance_score"] = insights.quality_thresholds["min_relevance_score"]
        prefs["quality"]["min_quality_score"] = insights.quality_thresholds["min_quality_score"]

        # Update article count targets
        prefs["output"]["max_articles"] = insights.optimal_article_count

        # Save updated preferences
        with open(self.preferences_file, "w") as f:
            yaml.safe_dump(prefs, f, default_flow_style=False)

        print(f"✅ Preferences updated and saved to {self.preferences_file}")
```

### Learning Report

```python
# Generate a report showing what the system learned

def generate_learning_report(insights: LearningInsights) -> str:
    """
    Create a human-readable report of what was learned
    """
    report = """
# Learning Report

Based on your feedback over the last 30 days, I've made the following adjustments:

## Topic Priority Adjustments
"""

    for topic, new_priority in insights.topic_weights.items():
        old_priority = get_current_priority(topic)
        if new_priority > old_priority:
            report += f"- ⬆️ **{topic}**: Increased priority to {new_priority}/10 (you seem to enjoy this)\n"
        elif new_priority < old_priority:
            report += f"- ⬇️ **{topic}**: Decreased priority to {new_priority}/10 (you rarely read these)\n"

    report += "\n## Source Trust Adjustments\n"

    for source, trust in sorted(insights.source_trust.items(), key=lambda x: x[1], reverse=True):
        if trust > 0.8:
            report += f"- ⭐ **{source}**: High trust ({trust*100:.0f}%) - you rate these highly\n"
        elif trust < 0.4:
            report += f"- ⚠️ **{source}**: Low trust ({trust*100:.0f}%) - consider removing?\n"

    report += f"\n## Optimal Article Count\n"
    report += f"Adjusted max articles to **{insights.optimal_article_count}** based on your reading patterns.\n"

    report += f"\n## Quality Thresholds\n"
    report += f"- Relevance threshold: {insights.quality_thresholds['min_relevance_score']:.2f}\n"
    report += f"- Quality threshold: {insights.quality_thresholds['min_quality_score']:.2f}\n"

    return report
```

---

## Database Schema

```sql
-- data/feedback.db

CREATE TABLE digests (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    accessed_at TIMESTAMP,
    article_count INTEGER
);

CREATE TABLE articles (
    id TEXT PRIMARY KEY,
    digest_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    topic TEXT NOT NULL,
    url TEXT NOT NULL,
    system_relevance_score REAL,
    system_quality_score REAL,
    FOREIGN KEY (digest_id) REFERENCES digests(id)
);

CREATE TABLE passive_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_accessed BOOLEAN DEFAULT FALSE,
    time_spent_seconds INTEGER,
    scroll_depth REAL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE active_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    relevance_rating INTEGER CHECK (relevance_rating BETWEEN 1 AND 5),
    quality_rating INTEGER CHECK (quality_rating BETWEEN 1 AND 5),
    bias_accuracy_rating INTEGER CHECK (bias_accuracy_rating BETWEEN 1 AND 5),
    marked_favorite BOOLEAN DEFAULT FALSE,
    marked_irrelevant BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE learning_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    insights_json TEXT,  -- JSON of LearningInsights
    changes_applied TEXT  -- Human-readable description
);

CREATE INDEX idx_passive_tracking_article ON passive_tracking(article_id);
CREATE INDEX idx_active_feedback_article ON active_feedback(article_id);
CREATE INDEX idx_articles_digest ON articles(digest_id);
```

---

## Privacy Considerations

### Data Storage
- All feedback stored **locally only** (SQLite database)
- No external tracking or telemetry
- No cloud sync unless explicitly enabled by user
- API keys never logged

### Data Retention
- Active feedback: **Kept forever** (needed for learning)
- Passive tracking: **30 days** (then aggregated to statistics)
- Articles: **30 days** (content deleted, metadata kept)
- Digests: **Forever** (markdown files)

### User Control
- Can export all feedback data (JSON)
- Can delete individual feedback entries
- Can reset learning and start over
- Can disable learning entirely (passive tracking only)

---

## Summary: Passive vs. Active

| Aspect | Passive Tracking | Active Feedback |
|--------|-----------------|-----------------|
| **Phase** | 1-4 | 5+ |
| **User Effort** | None | 30 seconds per article |
| **Data Collected** | Access times, reading duration | Ratings (1-5), favorites, notes |
| **Accuracy** | Moderate (inferred) | High (explicit) |
| **Learning Power** | Basic patterns | Deep personalization |
| **When to Use** | Early stages | After 2+ weeks of use |

---

**Document Version:** 2.0
**Last Updated:** October 23, 2025
