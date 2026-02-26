# Social Media Manager Skill - Silver Tier US2

**Purpose**: Create and manage multi-platform social media posts for LinkedIn, Facebook, and Twitter.

**Capability**: Silver Tier - Autonomous social media posting with Human-in-the-Loop (HITL) approval.

---

## Overview

The Social Media Manager enables the AI Employee to post content across multiple platforms simultaneously. Posts are created in `/Needs_Action/`, approved by moving to `/Approved/`, and executed automatically via MCP servers.

**Supported Platforms**:
- **LinkedIn**: Professional networking (limit: 3000 chars)
- **Facebook**: Social networking (limit: 63,206 chars)
- **Twitter/X**: Microblogging (limit: 280 chars, auto-threading for longer content)

**Core Workflow**:
1. AI creates social media post plan in `/Needs_Action/`
2. Human reviews content and target platforms
3. Human moves plan to `/Approved/` (approval signal)
4. Executor detects and validates post
5. Posts to each platform via MCP servers
6. Tracks per-platform results
7. Moves to `/Done/` with platform_results

---

## Creating Social Media Posts

### Post Plan Format

**File**: `POST_[platform]_[timestamp].md` in `/Needs_Action/`

**Frontmatter Schema**:
```yaml
type: social_media_post
post_id: POST_linkedin_1735144800
platforms: [linkedin, facebook, twitter]
status: draft
created_at: 2026-02-25T14:30:00Z
```

**Optional Fields**:
```yaml
scheduled_time: 2026-02-26T09:00:00Z  # Post at specific time
media_attachments:
  - url: https://example.com/image.png
    type: image
    alt_text: Product screenshot
```

**Body**: Post content (plain text or markdown)

### Example: Simple LinkedIn Post

```markdown
---
type: social_media_post
post_id: POST_linkedin_1735144800
platforms: [linkedin]
status: draft
created_at: 2026-02-25T14:30:00Z
---

Excited to announce the launch of our AI Employee system!

This revolutionary tool helps automate:
- Email triage and responses
- File processing
- Social media posting

Learn more: https://example.com/ai-employee

#AI #Automation #ProductLaunch
```

### Example: Multi-Platform Post

```markdown
---
type: social_media_post
post_id: POST_linkedin_1735144820
platforms: [linkedin, facebook, twitter]
status: draft
created_at: 2026-02-25T14:35:00Z
media_attachments:
  - url: https://example.com/dashboard.png
    type: image
    alt_text: AI Employee Dashboard
---

🚀 New Feature Alert!

Our AI Employee now supports multi-platform social media posting. One click, three platforms.

Try it today: https://example.com/signup
```

### Example: Scheduled Post

```markdown
---
type: social_media_post
post_id: POST_twitter_1735144840
platforms: [twitter]
status: draft
scheduled_time: 2026-02-26T09:00:00Z  # Post tomorrow at 9 AM
created_at: 2026-02-25T14:40:00Z
---

Good morning! Starting the day with some exciting AI news...

(Thread continues...)
```

---

## Platform-Specific Validation

### Character Limits

Each platform has different content length restrictions:

| Platform | Limit | Behavior if Exceeded |
|----------|-------|---------------------|
| LinkedIn | 3,000 | Validation error, post rejected |
| Facebook | 63,206 | Validation error, post rejected |
| Twitter | 280 | Auto-split into thread (see below) |

**Validation Process**:
1. Executor checks content length against platform limits
2. If any platform rejects, entire post is moved to `/Needs_Action/` with error
3. User must shorten content or remove platform from `platforms` list

### Twitter Threading

**Automatic Threading**: Content >280 characters is automatically split into a thread.

**Algorithm**:
1. Split content by words
2. Group words into tweets ≤280 chars (accounting for thread counter)
3. Add thread counters: " (1/3)", " (2/3)", " (3/3)"
4. Post as threaded reply chain

**Example**:

**Input** (400 characters):
```
This is a long announcement about our new product. It has many features including
email automation, file processing, social media posting, and scheduled tasks. We're
very excited to share this with the world and can't wait to see how it helps teams
work more efficiently!
```

**Output** (3 tweets):
```
Tweet 1: This is a long announcement about our new product. It has many features
including email automation, file processing, social media posting, and scheduled
tasks. We're very excited to share this with the (1/3)

Tweet 2: world and can't wait to see how it helps teams work more efficiently! (2/3)

Tweet 3: Learn more at https://example.com (3/3)
```

### Media Attachments

**Supported Types**:
- `image`: PNG, JPG, GIF
- `video`: MP4, MOV
- `document`: PDF (LinkedIn only)

**Format**:
```yaml
media_attachments:
  - url: https://example.com/photo.jpg
    type: image
    alt_text: Descriptive text for accessibility
  - url: https://example.com/video.mp4
    type: video
```

**Platform Support**:
- **LinkedIn**: All types (images, videos, documents)
- **Facebook**: Images and videos only
- **Twitter**: Images and videos only (max 4 images per tweet)

**Note**: Media must be publicly accessible URLs. MCP servers fetch media from URL.

---

## Execution & Results Tracking

### Per-Platform Results

After execution, the post file is updated with platform-specific results:

```yaml
platform_results:
  linkedin:
    platform: linkedin
    status: success
    post_url: https://linkedin.com/posts/123456
    post_id: urn:li:share:123456
    posted_at: 2026-02-25T14:35:22Z
  twitter:
    platform: twitter
    status: success
    post_url: https://twitter.com/user/status/987654
    post_id: '987654'
    posted_at: 2026-02-25T14:35:25Z
  facebook:
    platform: facebook
    status: failed
    error: Rate limit exceeded - wait 300s
    posted_at: 2026-02-25T14:35:28Z
```

**Status Values**:
- `success`: Posted successfully
- `failed`: Post failed (see `error` field)
- `pending`: Not yet attempted

### Post Status Transitions

```
draft → approved → posted    (all platforms succeeded)
draft → approved → partial   (some platforms succeeded)
draft → approved → failed    (all platforms failed)
```

**Partial Success Handling**:
- Post moves to `/Done/` even if some platforms failed
- User can review `platform_results` to see which succeeded
- Failed platforms show error messages
- User can retry failed platforms by creating new post (copy content)

---

## Error Scenarios & Recovery

### Error Type 1: Content Too Long

**Symptoms**: Post rejected with validation error

**Error Message**:
```yaml
error_details: "Content too long for twitter: 350 chars (limit: 280)"
```

**Recovery**:
1. Review content length: `350 chars (limit: 280)`
2. **Option A**: Shorten content to fit Twitter limit
3. **Option B**: Remove Twitter from platforms list (post to LinkedIn/Facebook only)
4. **Option C**: Let Twitter auto-thread (no action needed - threading is automatic)

### Error Type 2: Rate Limit Exceeded

**Symptoms**: One or more platforms show rate limit error

**Error Message**:
```yaml
linkedin:
  status: failed
  error: Rate limit exceeded - wait 3600s
```

**Rate Limits**:
- LinkedIn: 100 posts/day
- Facebook: 200 posts/day
- Twitter: 2400 tweets/day

**Recovery**:
1. Wait for rate limit reset (tokens replenish continuously)
2. Check remaining quota: `cat vault/Logs/rate_limit_state.json`
3. Plan moves to `/Needs_Action/`, can be re-approved when ready

### Error Type 3: MCP Server Unreachable

**Symptoms**: All platforms fail with connection error

**Error Message**:
```yaml
error_details: "Connection error: LinkedIn MCP server unreachable"
```

**Recovery**:
1. Check MCP server status: `curl http://localhost:3002/linkedin/health`
2. Verify MCP URLs in `.env` are correct
3. Restart MCP servers if needed
4. Re-approve post (move back to `/Approved/`)

### Error Type 4: Platform API Error

**Symptoms**: Platform-specific API error (e.g., authentication failed, content rejected)

**Error Message**:
```yaml
facebook:
  status: failed
  error: "Content violates platform guidelines"
```

**Recovery**:
1. Review platform's content policy
2. Modify content to comply
3. Create new post (do not reuse same post ID)

### Error Type 5: Scheduled Post Not Ready

**Symptoms**: Post skipped with log message "scheduled for future"

**Behavior**:
- Executor detects `scheduled_time` is in the future
- Post stays in `/Approved/` (not moved)
- Executor will process when scheduled time arrives

**Note**: Scheduled posts are checked every time executor scans `/Approved/` (every ~5 seconds).

---

## Platform-Specific Best Practices

### LinkedIn

**Best Practices**:
- Use professional tone
- Include relevant hashtags (3-5 max)
- Tag people/companies with `@mention`
- Add link to article/product at end
- Include call-to-action

**Optimal Length**: 150-300 characters (higher engagement)

**Example**:
```markdown
Excited to share insights from our latest AI research!

Key findings:
✓ 40% productivity increase
✓ 95% accuracy rate
✓ Cost reduction of 60%

Read the full report: https://example.com/research

#AI #MachineLearning #Research @CompanyName
```

### Facebook

**Best Practices**:
- Conversational tone
- Ask questions to encourage engagement
- Use emojis sparingly
- Include photos/videos for higher reach
- Keep important info in first 2 lines (above "See More")

**Optimal Length**: 40-80 characters (highest engagement)

**Example**:
```markdown
🎉 Big news! We just launched our new feature.

What do you think? Comment below! 👇

Learn more: https://example.com/feature
```

### Twitter

**Best Practices**:
- Concise and punchy
- Use relevant hashtags (1-2 max)
- Include media (images/videos increase engagement 3x)
- Thread long content (automatic)
- Engage with replies

**Optimal Length**: 100-280 characters (use full limit)

**Threading Tips**:
- Each tweet should make sense standalone
- Use numbered threads for tutorials/lists
- Add context at the end of thread

**Example Thread**:
```markdown
Thread: How to build an AI Employee in 2026

1/ Start with a clear use case. Don't try to automate everything at once.

2/ Use local-first architecture. Your data stays on your machine.

3/ Implement HITL (Human-in-the-Loop) for critical actions. AI proposes, you approve.

4/ Build incrementally. Bronze → Silver → Gold tiers.

End/ Try it yourself: https://example.com/tutorial
```

---

## Rate Limiting Details

### Token Bucket Algorithm

Each platform has its own token bucket:
- **Capacity**: Daily limit (LinkedIn: 100, Facebook: 200, Twitter: 2400)
- **Refill Rate**: Continuous (capacity / 86400 seconds)
- **Consumption**: 1 token per post

**State File**: `/Logs/rate_limit_state.json`

**Example State**:
```json
{
  "linkedin": {
    "platform": "linkedin",
    "capacity": 100,
    "tokens": 87.3,
    "total_consumed": 13,
    "last_reset": 1735142400
  }
}
```

**Behavior**:
- Tokens refill continuously (not all at once)
- If tokens < 1, post is blocked until refill
- State persists across executor restarts

---

## Monitoring & Audit Logs

### Execution Logs

Every social media post creates an audit log:

```json
{
  "log_id": "LOG_1735144800_social_post",
  "timestamp": "2026-02-25T14:30:00Z",
  "action_type": "social_post",
  "actor": "executor",
  "plan_id": "POST_linkedin_123456.md",
  "target": "linkedin, twitter",
  "parameters": {
    "platforms": ["linkedin", "twitter"],
    "content_preview": "Excited to announce the launch...",
    "needs_thread": false
  },
  "result": "partial",
  "mcp_server": "multiple",
  "response": {
    "platform_results": {
      "linkedin": {"status": "success", "post_url": "..."},
      "twitter": {"status": "failed", "error": "..."}
    }
  },
  "duration_ms": 3250,
  "retry_count": 0
}
```

### Dashboard Integration

Social media statistics appear on Dashboard.md:

```markdown
## Social Media Statistics

- **Posts Published Today**: 12 posts
- **Platforms**: LinkedIn (5), Twitter (4), Facebook (3)
- **Last Post**: 14:30 (30 minutes ago)
- **Success Rate**: 92% (11/12 successful)
```

---

## Claude Code Integration

When creating social media posts, Claude Code should:

### 1. Use the Template

```markdown
---
type: social_media_post
post_id: POST_{{ platform }}_{{ timestamp }}
platforms: [{{ platforms }}]
status: draft
created_at: {{ iso_timestamp }}
---

{{ post_content }}
```

### 2. Choose Appropriate Platforms

**Decision Tree**:
- Professional announcement? → LinkedIn
- Casual update? → Facebook
- Quick news/link? → Twitter
- Company update? → All three

### 3. Validate Content Length

Before creating post, check:
```python
content_length = len(post_content)

if 'linkedin' in platforms and content_length > 3000:
    # Shorten or remove LinkedIn

if 'facebook' in platforms and content_length > 63206:
    # Shorten or remove Facebook

if 'twitter' in platforms and content_length > 280:
    # Will auto-thread, inform user
```

### 4. Include Context

Add helpful metadata:
```yaml
original_request: "Announce new feature launch"
target_audience: "Existing customers and prospects"
call_to_action: "Visit website to learn more"
```

### 5. Place in Correct Folder

- Create in `/Needs_Action/` (NOT `/Approved/`)
- Human must manually approve
- Do not auto-approve (Silver Tier restriction)

---

## Security & Privacy

### Content Guidelines

**Do Not Post**:
- Confidential information
- Customer data
- API keys or credentials
- Unreleased product details
- Personal information

**Do Post**:
- Public announcements
- Blog post links
- Product launches
- Company updates
- Thought leadership

### Approval Workflow

**No Auto-Approval**: Every post requires human review (Silver Tier)

**Human Must**:
1. Review content for accuracy
2. Check platform appropriateness
3. Verify links work
4. Approve by moving to `/Approved/`

**Gold Tier** (future): Auto-approve low-risk posts based on rules

---

## Future Enhancements (Gold Tier)

- **Auto-Approval**: Configure rules for auto-approving specific content types
- **Scheduling Engine**: Queue multiple posts for future dates/times
- **A/B Testing**: Post variants to test engagement
- **Analytics**: Track engagement metrics (likes, shares, comments)
- **Content Library**: Reuse evergreen content
- **Hashtag Suggestions**: AI-powered hashtag recommendations

---

**Version**: Silver Tier 0.2.0
**Last Updated**: 2026-02-25
**Related**: executor-skill.md, vault-manager.md
