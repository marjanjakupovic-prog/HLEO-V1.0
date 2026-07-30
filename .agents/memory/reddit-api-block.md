---
name: Reddit API block
description: Reddit public JSON API returns 403 from Replit; approach to fix
---

## Problem
Reddit's unauthenticated JSON API (`reddit.com/search.json`) returns HTTP 403 from Replit's IP range. Even with a Firefox User-Agent header the response is 403.

## Fix required
Use Reddit's official OAuth2 API via PRAW (Python Reddit API Wrapper):
1. Register a Reddit app at https://www.reddit.com/prefs/apps (script type)
2. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` as Replit secrets
3. Replace `collectors/reddit.py` with PRAW-based collector using `reddit.subreddit("all").search(query)`

**Why:** Reddit aggressively blocks datacenter IPs using the public JSON endpoint. PRAW uses OAuth which is accepted regardless of IP origin.

**Alternative:** Use Pushshift API or a Reddit-approved research data API, but PRAW is the most reliable long-term solution.
