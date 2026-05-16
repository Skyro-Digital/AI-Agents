# Mentor Brief — Config

Update this file with your actual mentors, Slack channels, and Fathom attendee names before running `/mentor-brief`.

---

## Mentors

| Name | Slack Username | Notes |
|------|---------------|-------|
| [Mentor Name] | @mentor_slack_username | [e.g. mastermind group, business coach] |
| [Mentor Name] | @mentor2_username | [e.g. e-commerce community] |
| [Mentor Name] | @mentor3_username | [e.g. agency peer group] |

---

## Slack Channels to Monitor

| Channel Name | Channel ID | Mentors Active Here |
|-------------|-----------|---------------------|
| #[channel-name] | C0XXXXXXXXX | [Mentor names] |
| #[channel-name] | C0XXXXXXXXY | [Mentor names] |
| #[channel-name] | C0XXXXXXXXZ | [Mentor names] |

**How to find a channel ID**: Right-click any channel in Slack → "Copy link" → the ID is the last segment of the URL (starts with C, e.g. `C0123456789`).

**Bot access**: Before running, invite the Skyro Mentor bot to each private channel via `/invite @[bot-name]` in Slack.

---

## Fathom Call Attendee Names

List mentor names exactly as they appear in Fathom call recordings (partial matches work — use first name if unsure):

- [Mentor First Last as shown in Fathom]
- [Another Mentor Name]
- [Another Mentor Name]

**How to check**: Open any past Fathom call → look at the speaker labels in the transcript sidebar.

---

## Notes

- The skill filters for HIGH and MEDIUM relevance content only — messages unrelated to your stated bottlenecks are counted but not shown
- To adjust the timeframe: `/mentor-brief 14d [topics]` for 14 days (default is 7)
- To focus on specific topics without the prompt: `/mentor-brief churn rate, team hiring`
