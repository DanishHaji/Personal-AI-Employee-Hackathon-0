# Social Media Integration Guide (Silver Tier)

## 🎯 Social Media Platforms Explained

Is project mein **4 social media platforms** support hain (Silver Tier feature):

1. **LinkedIn** 📊
2. **Facebook** 👥
3. **Twitter/X** 🐦
4. **WhatsApp** 💬

---

## 📱 Platform Details

### 1. LinkedIn (Professional Networking)

**Kya hai**: Professional business network
**Kya kar sakte ho**: Auto-post company updates, job postings, articles

**API Setup** (Production):
```bash
# .env mein add karo
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
LINKEDIN_ACCESS_TOKEN=your-access-token
```

**Use Case Examples**:
- Company milestones post karo
- Blog articles share karo
- Job openings announce karo
- Industry insights share karo

**Code Location**: `src/services/social_media_service.py`

**Example Post**:
```markdown
---
post_id: POST_001
platform: linkedin
status: pending_approval
scheduled_time: 2026-03-05T10:00:00
---

# Post: Company Milestone

Just crossed 10,000 customers! 🎉

Thank you to our amazing community for the support.

Here's to the next 10k! 🚀

#milestone #startup #growth
```

---

### 2. Facebook (Social Network)

**Kya hai**: General social media platform
**Kya kar sakte ho**: Business page updates, events, photos

**API Setup** (Production):
```bash
# .env mein add karo
FACEBOOK_PAGE_ID=your-page-id
FACEBOOK_ACCESS_TOKEN=your-access-token
```

**Use Case Examples**:
- Event announcements
- Product launches
- Community updates
- Customer stories

**Rate Limit**: 200 posts/day

---

### 3. Twitter/X (Microblogging)

**Kya hai**: Short-form updates (280 characters)
**Kya kar sakte ho**: Quick updates, announcements, engagement

**API Setup** (Production):
```bash
# .env mein add karo
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_SECRET=your-access-secret
```

**Use Case Examples**:
- Product updates
- Quick announcements
- Industry commentary
- Engagement with followers

**Rate Limit**: 2400 tweets/day
**Character Limit**: 280 characters

---

### 4. WhatsApp Business (Messaging)

**Kya hai**: Business messaging platform
**Kya kar sakte ho**: Customer support, notifications

**API Setup** (Production):
```bash
# .env mein add karo
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_ACCESS_TOKEN=your-access-token
WHATSAPP_BUSINESS_ACCOUNT_ID=your-account-id
```

**Use Case Examples**:
- Customer support messages
- Order confirmations
- Appointment reminders
- Incoming message monitoring

**Rate Limit**: 1000 messages/day (inbound monitoring)

---

## 🧪 Test Mode (Without APIs)

Abhi production APIs nahi hain, toh **mock mode** mein test kar sakte ho:

### Test Social Media Post

```bash
# Create mock social media post file
cat > test-vault/Needs_Action/SOCIAL_linkedin_milestone.md <<EOF
---
post_id: SOCIAL_001
type: social_media_post
platform: linkedin
status: pending_approval
scheduled_time: 2026-03-05T10:00:00
created: 2026-03-04T19:00:00
---

# Social Media Post: LinkedIn

**Platform**: LinkedIn
**Status**: Awaiting Approval

## Content

Just hit 10,000 users! 🎉

Big thanks to our amazing community.

Next milestone: 100k!

#startup #milestone #growth

---

**Approval Required**: Move to /Approved/ to post
EOF
```

Ye file **Silver Tier approval workflow** demonstrate karti hai.

---

## 🔧 How It Works (Architecture)

### Workflow:

```
1. Create Post Request
   └─→ File in /Needs_Action/

2. Review Post
   └─→ Human checks content

3. Approve Post
   └─→ Move to /Approved/

4. Executor Runs
   └─→ Detects approved post
   └─→ Calls Social Media API
   └─→ Post published

5. Confirmation
   └─→ Move to /Done/
   └─→ Audit log updated
```

### Trust Rules (Gold Tier):

Agar **trust rules** configure hain, toh automatic post kar sakta hai:

```yaml
# Company_Handbook.md mein
trust_rules:
  - rule_id: RULE_auto_post_linkedin
    rule_name: "Auto-post to LinkedIn"
    action_type: social_media_post
    trust_level: 1
    content_pattern: "#milestone|#achievement"
    platform: linkedin
    enabled: true
```

Isse milestone posts **automatically publish** ho jayengi (no manual approval).

---

## 📊 Social Media Service Code

**File**: `src/services/social_media_service.py`

**Functions**:
- `post_to_linkedin()` - LinkedIn par post karo
- `post_to_facebook()` - Facebook par post karo
- `post_to_twitter()` - Twitter par tweet karo
- `send_whatsapp_message()` - WhatsApp message bhejo

**Rate Limiting**: `src/services/rate_limiter.py` mein configured hai

---

## 🎯 Use Cases (Real Examples)

### Use Case 1: Weekly Blog Post

```bash
# Every Friday, auto-post new blog to LinkedIn
cat > test-vault/Plans/PLAN_weekly_blog.md <<EOF
---
plan_id: PLAN_blog_001
type: scheduled_task
schedule: "0 10 * * 5"  # Friday 10am
---

# Weekly Blog Post to LinkedIn

1. Fetch latest blog from website
2. Generate LinkedIn post with summary
3. Add relevant hashtags
4. Schedule for approval
5. Post if auto-approved
EOF
```

### Use Case 2: Customer Support (WhatsApp)

```bash
# Monitor WhatsApp for customer queries
# WhatsApp watcher running in background
# Detects: "Order status?"
# Auto-reply: "Let me check your order..."
```

### Use Case 3: Product Launch

```bash
# Multi-platform announcement
cat > test-vault/Needs_Action/SOCIAL_product_launch.md <<EOF
---
post_id: SOCIAL_launch_001
platforms:
  - linkedin
  - twitter
  - facebook
scheduled_time: 2026-03-10T09:00:00
---

# Product Launch Announcement

🚀 Launching our new AI feature today!

Try it now: https://ourapp.com/ai

#AI #ProductLaunch #Innovation
EOF
```

---

## ⚠️ Important Notes

### 1. API Keys Required

Production mein **real API keys** chahiye:
- LinkedIn: https://www.linkedin.com/developers/
- Facebook: https://developers.facebook.com/
- Twitter: https://developer.twitter.com/
- WhatsApp: https://business.whatsapp.com/

### 2. Rate Limits

Har platform ki limits hain (managed by `rate_limiter.py`):
- LinkedIn: 100 posts/day
- Facebook: 200 posts/day
- Twitter: 2400 tweets/day
- WhatsApp: 1000 messages/day

### 3. Approval Workflow (Silver Tier)

**Default**: Har post ko manual approval chahiye
**With Trust Rules (Gold)**: Auto-approve specific types

### 4. Content Guidelines

- ✅ Keep it professional (LinkedIn)
- ✅ Add hashtags for reach
- ✅ Include call-to-action
- ✅ Check character limits (Twitter: 280)
- ❌ No spam/promotional overload

---

## 🔍 Testing Social Media (Without APIs)

**Mock Test File**:

```bash
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# Create test social media post
cat > test-vault/Needs_Action/SOCIAL_test_post.md <<EOF
---
post_id: SOCIAL_TEST_001
type: social_media_post
platform: linkedin
status: pending_approval
created: 2026-03-04T20:00:00
---

# Test Social Media Post

**Platform**: LinkedIn
**Type**: Company Update

## Content

Testing AI Employee social media automation! 🤖

This post was generated automatically by our AI system.

Pretty cool, right?

#AI #Automation #Testing

---

**Next Steps**:
1. Review content ✓
2. Move to /Approved/ to simulate posting
3. Check audit log for confirmation
EOF

echo "✅ Created test social media post"
echo "   File: test-vault/Needs_Action/SOCIAL_test_post.md"
echo "   Platform: LinkedIn"
echo "   Status: Pending Approval"
```

**Simulate Approval**:

```bash
# Move to approved folder (simulates human approval)
mv test-vault/Needs_Action/SOCIAL_test_post.md \
   test-vault/Approved/

# In production, executor would detect this and call LinkedIn API
# Since no API, we simulate success:
mv test-vault/Approved/SOCIAL_test_post.md \
   test-vault/Done/

echo "✅ Social media post 'published' (simulated)"
```

---

## 📈 Analytics & Tracking

Social media posts ko track karo:

**Metrics** (stored in audit log):
- Posts published
- Platforms used
- Engagement (if API provides)
- Best posting times
- Popular content types

**Example Audit Entry**:
```json
{
  "timestamp": "2026-03-04T20:00:00",
  "event": "social_media_post",
  "platform": "linkedin",
  "post_id": "SOCIAL_001",
  "status": "published",
  "engagement": {
    "likes": 42,
    "comments": 8,
    "shares": 3
  }
}
```

---

## 🚀 Next Steps

### To Enable Social Media:

1. **Get API Keys**:
   - Register apps on each platform
   - Get OAuth tokens
   - Add to `.env` file

2. **Configure Rate Limits**:
   - Already configured in `rate_limiter.py`
   - Monitors daily quota

3. **Set Trust Rules** (Optional):
   - Auto-approve certain types
   - Requires Gold Tier

4. **Start Posting**:
   - Create post files
   - Review and approve
   - AI publishes automatically

---

## 💡 Pro Tips

1. **Batch Posts**: Schedule multiple posts for the week
2. **Time Zones**: Consider audience timezone
3. **Hashtag Research**: Use trending hashtags
4. **Visual Content**: Add images/videos (if API supports)
5. **Engagement**: Monitor replies and respond
6. **Analytics**: Track what works best

---

## ❓ FAQ

**Q: Kya bina API ke test kar sakte hain?**
A: Haan! Mock files create karke workflow test kar sakte ho.

**Q: Kitne platforms support hain?**
A: 4 platforms - LinkedIn, Facebook, Twitter, WhatsApp

**Q: Kya automatically post hota hai?**
A: Silver Tier: Manual approval chahiye
   Gold Tier: Trust rules se auto-post ho sakta hai

**Q: Rate limits kya hain?**
A: Platform-specific (100-2400 posts/day)

**Q: Kaise setup kare?**
A: API keys lo → .env mein add karo → social_media_service.py use karo

---

## 📚 Resources

- LinkedIn API: https://docs.microsoft.com/linkedin/
- Facebook API: https://developers.facebook.com/docs/
- Twitter API: https://developer.twitter.com/en/docs
- WhatsApp API: https://developers.facebook.com/docs/whatsapp

---

**Summary**: Social media features Silver Tier mein hain. Production ke liye API keys chahiye, lekin test mode mein mock files se simulate kar sakte ho!
