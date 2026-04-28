---
name: find-contacts
description: Identify people at a target company that the candidate should find on LinkedIn. Use when the candidate asks "who should I reach out to at X", "find contacts at Y", or when preparing outreach for a company in the pipeline. Researches the company's team structure, identifies the right contact types by seniority and function, generates precise LinkedIn search queries for manual lookup, and writes results to the contacts table in pipeline.db.
---

# Find Contacts — Output Template

Identifies the right people to find at a target company, generates LinkedIn
search queries for the candidate to run manually, and saves contact records to the database.

All voice rules and outreach logic are in CLAUDE.md.

## Step 1: Identify the Company

```python
import db.db as db
# Get company_id from pipeline — needed to save contacts
db.show_pipeline()
```

## Step 2: Research the Team

Use web search to find:
- LinkedIn company page: `site:linkedin.com/company [company name]`
- Team/About page on company website
- Recent press releases or blog posts with author names
- Conference talks or webinars (speakers are often decision-makers)
- Any PM, engineering, or product leadership visible publicly

Search queries:
- `"[Company]" "product manager" OR "head of product" site:linkedin.com`
- `"[Company]" "VP product" OR "CPO" OR "director of product"`
- `"[Company]" recruiter OR "talent" OR "people operations"`
- `[Company] product team blog OR engineering blog`

## Step 3: Identify Priority Contact Types

For each company, surface contacts in this priority order:

**Tier 1 — Highest value (the candidate should find these first)**
- Hiring manager for the specific role (often Director or VP of Product)
- CPO or Head of Product (if company is <200 people)
- Peer Senior PM or Principal PM on the team

**Tier 2 — Useful for intel and warm path**
- Engineering manager or VP Engineering (signals technical culture)
- Recruiter or Talent Partner handling the role
- Former employee now at another company (can give unfiltered context)

**Tier 3 — Good to know exist**
- CEO/Founder (for small companies where PM reports up close)
- Customer Success or Sales leaders (signals ICP and customer context)

## Step 4: Generate LinkedIn Search Queries

For each contact type identified, generate a precise LinkedIn search query
the candidate can paste directly into LinkedIn search:

Format: `[First Last] [Company]` if name is known
Format: `[Title] [Company]` if searching by role

Precision rules:
- Use current company name exactly as it appears on LinkedIn
- Include location filter suggestion if helpful ("+ Boise" or "+ Remote")
- Note if the person's profile may be hard to find (common name, private profile)

## Step 5: Write to Database

For each identified contact (even if LinkedIn URL unknown yet):

```python
contact_id = db.add_contact(
    company_id            = [id],
    name                  = "[name or 'Unknown — search by title']",
    title                 = "[title]",
    relationship          = "[hiring manager / recruiter / peer PM / leadership]",
    linkedin_search_query = "[exact search string to use]",
    notes                 = "[why this person, any context found]"
)
```

After the candidate finds them manually and gets the URL:
```python
db.update_contact_linkedin(contact_id, "https://linkedin.com/in/...")
```

## Output Format

```
## Contacts: [Company Name]
Company ID: [id] | Role: [role being pursued]

---

### Tier 1 — Find These First

**[Name if known / "Hiring Manager — Product" if unknown]**
- Title: [title]
- Why: [1 sentence — their relevance to the candidate's application]
- LinkedIn search: `[exact query to paste]`
- Context: [anything found — recent post, talk, article, mutual connection]
- DB contact_id: [id after db.add_contact()]

[Repeat for each Tier 1 contact]

---

### Tier 2 — Intel & Warm Path

**[Name/Role]**
- Title:
- Why:
- LinkedIn search: `[query]`
- DB contact_id: [id]

---

### Tier 3 — Good to Know

[List names/titles and search queries only — less detail needed]

---

### After You Find Them

For each contact found on LinkedIn, run:
```python
db.update_contact_linkedin([contact_id], "[linkedin URL]")
```

Then tell me which ones to prioritize for outreach — I'll run draft-outreach
using the hook and voice rules in CLAUDE.md.

---

### Outreach Sequencing Suggestion

[Given what was found, suggest who the candidate should message first and why —
e.g., "Start with the recruiter to confirm the role is still open, then
reach out to the hiring manager with the specific hook identified in
company-research."]
```

## Notes

- Never fabricate contact names — only surface people found through research
- If a company has limited public team visibility, note it and suggest
  the candidate check LinkedIn's "People" tab on the company page directly
- For very small companies (<50 people), CEO/founder outreach is reasonable
- Flag if any contact appears to have left the company recently
  (check for "Former" in their title or recent job change activity)
- Always save contact records to DB even without LinkedIn URL —
  the record exists so the candidate can add the URL after manual lookup

## Output Persistence (Auto-Save)

After generating the contacts list, automatically save it:

1. **Write markdown file** to `references/analyses/{role-id:03d}-{company-slug}-contacts-{date}.md`
2. **Log to database** via `db.log_find_contacts_run`:
   ```python
   import db.db as db
   db.log_find_contacts_run(
       role_id   = role_id,
       file_path = f"references/analyses/{role_id:03d}-{slug}-contacts-{date}.md",
   )
   ```
3. **Update contacts with discovery info** when the candidate finds LinkedIn URLs:
   ```python
   # Mark as priority target
   db.update_contact_discovered(contact_id, "https://linkedin.com/in/...", is_target=True)

   # Later, when outreach is sent
   db.update_contact_outreach(contact_id, response_received=False)
   ```

No user confirmation required.
