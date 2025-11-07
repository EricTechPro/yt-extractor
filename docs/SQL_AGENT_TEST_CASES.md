# SQL Agent Test Cases - YouTube Comments Database

## Test Suite Overview

This document contains comprehensive test cases for validating the SQL agent's ability to query and analyze YouTube comments data stored in Supabase. Each test case includes the natural language question, expected SQL capabilities, and validation criteria.

---

## Database Schema Quick Reference

**Tables:**
- `comments`: Top-level comments (columns: `channel_id`, `youtube_comment_id`, `comment`, `videoTitle`, `videoLink`, `datePostComment`, `likesCount`)
- `sub_comments`: Replies (columns: `channel_id`, `youtube_comment_id`, `subComment`, `parentCommentId`, `videoTitle`, `videoLinkId`, `datePostSubComment`, `likeCount`)

**Relationship:** `comments.youtube_comment_id` ↔ `sub_comments.parentCommentId` (One-to-Many)

---

## Test Cases

| # | Question | AI Capability Tested | SQL Conditions | Function Used | Pass ✅ |
|---|----------|---------------------|----------------|---------------|---------|
| **BASIC FILTERING** |
| 1 | What are all comments for the video titled "Introduction to Python"? | **Filter** by exact text match | `WHERE videoTitle = 'Introduction to Python'` | SELECT | ☐ |
| 2 | Show me comments posted after January 1, 2024 | **Filter** by date comparison | `WHERE datePostComment > '2024-01-01'` | SELECT | ☐ |
| 3 | Find all comments with more than 100 likes | **Filter** by numeric threshold | `WHERE likesCount > 100` | SELECT | ☐ |
| 4 | Which comments were posted in December 2024? | **Filter** by date range | `WHERE datePostComment BETWEEN '2024-12-01' AND '2024-12-31'` | SELECT + BETWEEN | ☐ |
| **AGGREGATION FUNCTIONS** |
| 5 | How many total comments are in the database? | **Count** all records | `COUNT(*)` | COUNT() | ☐ |
| 6 | What's the average number of likes across all comments? | **Average** calculation | `AVG(likesCount)` | AVG() | ☐ |
| 7 | What is the total engagement (sum of all likes) for all comments? | **Sum** values | `SUM(likesCount)` | SUM() | ☐ |
| 8 | Which video has the most comments? | **Group by** + **Count** + **Sort** | `GROUP BY videoTitle ORDER BY COUNT(*) DESC LIMIT 1` | COUNT() + GROUP BY | ☐ |
| 9 | What's the most liked comment in the entire channel? | **Sort** and **Limit** | `ORDER BY likesCount DESC LIMIT 1` | MAX() or ORDER BY | ☐ |
| **MULTI-TABLE JOINS** |
| 10 | Show me all comments and their replies for video "Python Tutorial" | **Join** two tables with filter | `JOIN sub_comments ON youtube_comment_id = parentCommentId WHERE videoTitle = 'Python Tutorial'` | JOIN + SELECT | ☐ |
| 11 | How many replies does each comment have? | **Join** + **Group by** + **Count** | `LEFT JOIN sub_comments GROUP BY youtube_comment_id COUNT(sub_comments.id)` | LEFT JOIN + COUNT() | ☐ |
| 12 | Which comment has the most replies? | **Join** + **Group by** + **Sort** + **Limit** | `LEFT JOIN GROUP BY youtube_comment_id ORDER BY COUNT(sub_comments.id) DESC LIMIT 1` | LEFT JOIN + COUNT() + MAX() | ☐ |
| 13 | Find all comments that have NO replies | **Left join** with null check | `LEFT JOIN sub_comments WHERE sub_comments.id IS NULL` | LEFT JOIN + IS NULL | ☐ |
| 14 | What's the total engagement (parent likes + reply likes) for each video? | **Join** + **Sum** + **Group by** | `JOIN + SUM(likesCount) + SUM(likeCount) GROUP BY videoTitle` | JOIN + SUM() | ☐ |
| **TEMPORAL ANALYSIS** |
| 15 | Show comment activity by month in 2024 | **Date extraction** + **Group by** | `DATE_TRUNC('month', datePostComment) GROUP BY month` | DATE_TRUNC() + GROUP BY | ☐ |
| 16 | What day had the most comment activity? | **Date extraction** + **Count** + **Sort** | `DATE_TRUNC('day', datePostComment) GROUP BY day ORDER BY COUNT(*) DESC` | DATE_TRUNC() + COUNT() | ☐ |
| 17 | How long on average between a comment and its first reply? | **Join** + **Date difference** + **Average** | `JOIN AVG(sub_comments.datePostSubComment - comments.datePostComment)` | JOIN + DATE_DIFF + AVG() | ☐ |
| 18 | Which videos got comments most recently? | **Sort** by date descending | `ORDER BY datePostComment DESC` | SELECT + ORDER BY | ☐ |
| **SORTING & LIMITING** |
| 19 | Show me the top 10 most liked comments | **Sort** and **Limit** | `ORDER BY likesCount DESC LIMIT 10` | ORDER BY + LIMIT | ☐ |
| 20 | What are the 5 most recent replies? | **Sort** by date + **Limit** | `ORDER BY datePostSubComment DESC LIMIT 5` | ORDER BY + LIMIT | ☐ |
| 21 | Rank videos by total comment count (top 10) | **Group by** + **Count** + **Sort** + **Limit** | `GROUP BY videoTitle ORDER BY COUNT(*) DESC LIMIT 10` | COUNT() + GROUP BY + LIMIT | ☐ |
| **COMPLEX MULTI-FILTERS** |
| 22 | Find highly engaged recent comments (>50 likes AND posted in last 30 days) | **Multi-Filter** (numeric + date) | `WHERE likesCount > 50 AND datePostComment > NOW() - INTERVAL '30 days'` | SELECT + AND | ☐ |
| 23 | Which videos have both high comment count (>20) AND high average likes (>10)? | **Multi-Filter** with **Aggregation** | `GROUP BY videoTitle HAVING COUNT(*) > 20 AND AVG(likesCount) > 10` | GROUP BY + HAVING + COUNT() + AVG() | ☐ |
| 24 | Show conversation threads with >5 replies AND total thread engagement >100 | **Join** + **Multi-Filter** + **Aggregation** | `JOIN GROUP BY HAVING COUNT(sub_comments) > 5 AND SUM(all_likes) > 100` | JOIN + HAVING + COUNT() + SUM() | ☐ |
| 25 | Find comments with replies that are more liked than the parent | **Join** + **Comparison** + **Filter** | `JOIN WHERE sub_comments.likeCount > comments.likesCount` | JOIN + WHERE comparison | ☐ |
| **TEXT SEARCH & PATTERN MATCHING** |
| 26 | Find comments containing the word "tutorial" | **Text search** (case-insensitive) | `WHERE LOWER(comment) LIKE '%tutorial%'` | LIKE + LOWER() | ☐ |
| 27 | Which videos have "Python" in the title? | **Pattern matching** | `WHERE videoTitle ILIKE '%Python%'` | ILIKE | ☐ |
| 28 | Show all comments that ask questions (contain "?") | **Text pattern** matching | `WHERE comment LIKE '%?%'` | LIKE | ☐ |

---

## Advanced Insight Queries

These queries extract genuinely interesting insights from the channel:

| # | Insight Question | Purpose | Expected SQL Pattern | Pass ✅ |
|---|------------------|---------|---------------------|---------|
| A1 | What's the engagement rate (likes per comment) for each video? | Identify most engaging content | `SELECT videoTitle, COUNT(*) as comments, SUM(likesCount) as total_likes, (SUM(likesCount)::float / COUNT(*)) as engagement_rate GROUP BY videoTitle ORDER BY engagement_rate DESC` | ☐ |
| A2 | Which videos spark the most conversation (highest reply-to-comment ratio)? | Identify discussion-worthy content | `SELECT videoTitle, COUNT(DISTINCT comments.id) as comments, COUNT(sub_comments.id) as replies, (COUNT(sub_comments.id)::float / COUNT(DISTINCT comments.id)) as reply_ratio FROM comments LEFT JOIN sub_comments GROUP BY videoTitle ORDER BY reply_ratio DESC` | ☐ |
| A3 | What's the channel's comment growth trend by month? | Track channel growth over time | `SELECT DATE_TRUNC('month', datePostComment) as month, COUNT(*) as comment_count FROM comments GROUP BY month ORDER BY month` | ☐ |
| A4 | Which comments generated the most viral replies (replies with >50 likes)? | Find conversation starters | `SELECT comments.comment, comments.videoTitle, COUNT(sub_comments.id) as viral_replies FROM comments JOIN sub_comments ON comments.youtube_comment_id = sub_comments.parentCommentId WHERE sub_comments.likeCount > 50 GROUP BY comments.youtube_comment_id ORDER BY viral_replies DESC` | ☐ |
| A5 | What's the typical response time for this channel (time until first reply)? | Measure community responsiveness | `WITH first_replies AS (SELECT parentCommentId, MIN(datePostSubComment) as first_reply_time FROM sub_comments GROUP BY parentCommentId) SELECT AVG(first_replies.first_reply_time - comments.datePostComment) as avg_response_time FROM comments JOIN first_replies ON comments.youtube_comment_id = first_replies.parentCommentId` | ☐ |

---

## Testing Instructions

### How to Use This Test Suite

1. **Run Each Question Through SQL Agent**: Copy the question text from the "Question" column and submit to your n8n SQL agent
2. **Review Generated SQL**: Check if the agent generates SQL matching the "SQL Conditions" and uses the expected "Function Used"
3. **Verify Results**: Execute the query and verify it returns sensible results
4. **Mark Pass/Fail**: Check ✅ the "Pass" column if:
   - SQL syntax is valid
   - Query logic matches expected conditions
   - Results are accurate and meaningful
   - Performance is acceptable (<5 seconds for most queries)

### Success Criteria

- **Basic Competency**: Tests 1-9 should pass (filtering and basic aggregations)
- **Intermediate Competency**: Tests 10-21 should pass (joins, temporal, sorting)
- **Advanced Competency**: Tests 22-28 should pass (complex multi-filters and text search)
- **Expert Level**: Advanced insight queries A1-A5 should pass (complex business logic)

### Common Failure Patterns to Watch For

1. **Case Sensitivity Issues**: Agent doesn't handle `videoTitle` vs `videotitle`
2. **Join Logic Errors**: Wrong join type (INNER vs LEFT) or missing join conditions
3. **Date Format Problems**: Incorrect timestamp handling or timezone issues
4. **Aggregation Without GROUP BY**: Using COUNT/SUM/AVG without proper grouping
5. **NULL Handling**: Not accounting for NULL values in likes or dates
6. **String Matching**: Case-sensitive LIKE when ILIKE is needed

---

## Quick SQL Reference for This Schema

### Common Query Patterns

**Count comments per video:**
```sql
SELECT videoTitle, COUNT(*) as comment_count
FROM comments
GROUP BY videoTitle
ORDER BY comment_count DESC;
```

**Get comments with replies:**
```sql
SELECT c.comment, c.likesCount, COUNT(sc.id) as reply_count
FROM comments c
LEFT JOIN sub_comments sc ON c.youtube_comment_id = sc.parentCommentId
GROUP BY c.id;
```

**Temporal aggregation:**
```sql
SELECT DATE_TRUNC('day', datePostComment) as day, COUNT(*) as count
FROM comments
GROUP BY day
ORDER BY day DESC;
```

**Top engaged threads:**
```sql
SELECT
    c.comment,
    c.videoTitle,
    c.likesCount as parent_likes,
    COUNT(sc.id) as reply_count,
    COALESCE(SUM(sc.likeCount), 0) as reply_likes,
    (c.likesCount + COALESCE(SUM(sc.likeCount), 0)) as total_engagement
FROM comments c
LEFT JOIN sub_comments sc ON c.youtube_comment_id = sc.parentCommentId
GROUP BY c.id
ORDER BY total_engagement DESC
LIMIT 20;
```

---

## Notes

- **Field Name Casing**: All column names use camelCase exactly as shown (e.g., `videoTitle`, `likesCount`)
- **Date Fields**: All timestamps are `TIMESTAMPTZ` (timezone-aware)
- **Video Link Difference**: `comments.videoLink` is full URL, `sub_comments.videoLinkId` is just the ID
- **Foreign Key**: `sub_comments.parentCommentId` references `comments.youtube_comment_id`
- **Test Data**: Ensure you have sufficient test data across multiple videos and date ranges for accurate testing

---

**Last Updated**: 2025-11-06
**Database**: Supabase PostgreSQL
**Purpose**: Validate n8n SQL Agent capabilities for YouTube comment analysis
