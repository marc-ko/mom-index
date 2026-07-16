# Category Top Posts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the top 5 beginner-signal posts for every dashboard category and publish the static dashboard to GitHub Pages.

**Architecture:** Keep the existing single-file static dashboard. Change only the top-post rendering path so each sector renders its own group from `latest.sectors[sector].top_newbie_posts.slice(0, 5)`.

**Tech Stack:** Static HTML/CSS/JavaScript, Chart.js, Python `unittest` for regression checks, GitHub Pages on `gh-pages`.

## Global Constraints

- Do not alter generated raw data files unless publishing sanitized Pages data requires it.
- Preserve the existing bilingual labels and dashboard styling.
- Publish to the existing `marcko/gh-pages` branch.

---

### Task 1: Dashboard Top Posts Rendering

**Files:**
- Modify: `frontend/dashboard.html`
- Test: `tests/test_dashboard_top_posts.py`

**Interfaces:**
- Consumes: `dashboardData.latest.sectors` objects with `top_newbie_posts` arrays.
- Produces: grouped top-post HTML with one category section per sector and five posts per section.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dashboard_top_posts.py` with static assertions that require grouped rendering, a per-sector slice of 5, and no global merged `allTop.slice`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dashboard_top_posts -v`
Expected: FAIL because the current dashboard uses one merged `allTop` list.

- [ ] **Step 3: Write minimal implementation**

Update `renderTopPosts` in `frontend/dashboard.html` to iterate sectors and render each group independently.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dashboard_top_posts -v`
Expected: PASS.

- [ ] **Step 5: Publish**

Copy the updated static HTML and sanitized data to the `gh-pages` worktree, commit, and push `marcko gh-pages`.
