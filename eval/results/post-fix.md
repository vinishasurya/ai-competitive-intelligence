# Benchmark results — post-fix

10/10 products completed. Precision: strict = clearly-relevant only; lenient = not clearly irrelevant (defensible rubric). Pricing accuracy over 14 labeled tiers.

| Product | Group | Category OK | Precision (strict/lenient) | Pricing | Citations | Flags | Latency | Cost |
|---|---|---|---|---|---|---|---|---|
| linear.app | established | ✓ | 100% / 100% | 4/4 | 100% | 0 | 165s | 34¢ |
| slack.com | established | ✓ | 80% / 100% | — | 100% | 0 | 159s | 36¢ |
| notion.com | established | ✓ | 80% / 100% | 2/2 | 100% | 0 | 166s | 39¢ |
| figma.com | established | ✓ | 60% / 100% | — | 100% | 0 | 151s | 38¢ |
| tailscale.com | niche_b2b | ✓ | 100% / 100% | 4/4 | 100% | 0 | 158s | 41¢ |
| posthog.com | niche_b2b | ✓ | 100% / 100% | — | 100% | 0 | 148s | 36¢ |
| retool.com | niche_b2b | ✓ | 80% / 100% | — | 100% | 0 | 169s | 37¢ |
| cursor.com | recent | ✓ | 100% / 100% | — | 100% | 0 | 135s | 33¢ |
| lovable.dev | recent | ✓ | 80% / 100% | — | 100% | 1 | 142s | 31¢ |
| airtable.com | ambiguous | ✓ | 60% / 100% | 4/4 | 100% | 0 | 152s | 37¢ |

## Aggregate

| Metric | Value |
|---|---|
| Category accuracy | 100% |
| Competitor precision (strict) | 84% |
| Competitor precision (lenient) | 100% |
| Pricing accuracy | 100% (14 tiers) |
| Citation coverage | 100% |
| Validation flags (total) | 1 |
| Mean latency | 154.42s |
| Mean cost / report | 36.21¢ |

## Surfaced competitors and labels

**linear.app** — category: product development and issue tracking software for engineering teams
- Jira (atlassian.com): relevant
- Shortcut (shortcut.com): relevant
- Asana (asana.com): relevant
- GitHub (github.com): relevant
- ClickUp (clickup.com): relevant
- pricing linear.app 'Basic' expected $10.0, got $10.0 -> correct
- pricing linear.app 'Business' expected $16.0, got $16.0 -> correct
- pricing shortcut.com 'Team' expected $8.5, got $8.5 -> correct
- pricing shortcut.com 'Business' expected $12.0, got $12.0 -> correct
- pricing plane.so 'Pro' expected $6.0 -> not_evaluated
- pricing monday.com 'Basic' expected $9.0 -> not_evaluated
- pricing monday.com 'Standard' expected $12.0 -> not_evaluated

**slack.com** — category: AI-powered team collaboration and messaging platform for businesses
- Microsoft Teams (microsoft.com): relevant
- Mattermost (mattermost.com): relevant
- Rocket.Chat (rocket.chat): relevant
- Chanty (chanty.com): relevant
- Google Chat (workspace.google.com): defensible_unknown
- pricing twist.com 'Unlimited' expected $6.0 -> not_evaluated

**notion.com** — category: AI-powered all-in-one workspace and knowledge management software for teams
- Confluence (atlassian.com): relevant
- Coda (coda.io): relevant
- ClickUp (clickup.com): relevant
- Nuclino (nuclino.com): defensible_unknown
- Airtable (airtable.com): relevant
- pricing airtable.com 'Team' expected $20.0, got $20.0 -> correct
- pricing airtable.com 'Business' expected $45.0, got $45.0 -> correct
- pricing asana.com 'Starter' expected $10.99 -> not_evaluated
- pricing asana.com 'Advanced' expected $24.99 -> not_evaluated

**figma.com** — category: collaborative product design and development platform
- Sketch (sketch.com): relevant
- Penpot (penpot.app): relevant
- Uizard (uizard.io): defensible_unknown
- Adobe XD (adobe.com): relevant
- Balsamiq (balsamiq.com): defensible_unknown

**tailscale.com** — category: Zero Trust identity-based network connectivity platform (VPN/SASE/PAM replacement) for engineering, IT, and security teams
- Twingate (twingate.com): relevant
- NetBird (netbird.io): relevant
- OpenVPN (openvpn.net): relevant
- Cloudflare (cloudflare.com): relevant
- Zscaler (zscaler.com): relevant
- pricing tailscale.com 'Standard' expected $8.0, got $8.0 -> correct
- pricing tailscale.com 'Premium' expected $18.0, got $18.0 -> correct
- pricing twingate.com 'Teams' expected $5.0, got $5.0 -> correct
- pricing twingate.com 'Business' expected $10.0, got $10.0 -> correct
- pricing zerotier.com 'Professional' expected $2.0 -> not_evaluated

**posthog.com** — category: product analytics and developer data platform for product engineering teams
- Amplitude (amplitude.com): relevant
- Mixpanel (mixpanel.com): relevant
- Statsig (statsig.com): relevant
- LogRocket (logrocket.com): relevant
- FullStory (fullstory.com): relevant

**retool.com** — category: AI-native low-code platform for building internal apps, workflows, and agents
- Appsmith (appsmith.com): relevant
- Budibase (budibase.com): relevant
- OutSystems (outsystems.com): relevant
- Power Apps (powerapps.microsoft.com): defensible_unknown
- Superblocks (superblocks.com): relevant

**cursor.com** — category: AI-powered code editor and coding agent for software developers
- GitHub Copilot (github.com): relevant
- Tabnine (tabnine.com): relevant
- Zed (zed.dev): relevant
- Cognition (Devin) (cognition.ai): relevant
- Sourcegraph (sourcegraph.com): relevant

**lovable.dev** — category: AI-powered app builder / full-stack software development platform
- Bolt (bolt.new): relevant
- Replit (replit.com): relevant
- v0 by Vercel (v0.dev): relevant
- Bubble (bubble.io): relevant
- Softr (softr.io): defensible_unknown

**airtable.com** — category: no-code AI application and workflow platform for enterprise teams
- Monday.com (monday.com): relevant
- Smartsheet (smartsheet.com): relevant
- ClickUp (clickup.com): defensible_unknown
- Notion (notion.so): relevant
- Asana (asana.com): defensible_unknown
- pricing airtable.com 'Team' expected $20.0, got $20.0 -> correct
- pricing airtable.com 'Business' expected $45.0, got $45.0 -> correct
- pricing monday.com 'Basic' expected $9.0, got $9.0 -> correct
- pricing monday.com 'Standard' expected $12.0, got $12.0 -> correct
