# SG Wardrobe

A mobile-friendly AI personal stylist for Singapore. Live demo:
**<https://sg-wardrobe.vercel.app/>**

## Problem Statement

Deciding what to wear takes far too long. Many of us change in and out of
outfits every morning because nothing feels quite right, and talking to friends
showed this is a shared daily frustration. Singapore makes it harder: an outfit
has to survive a hot, humid walk outside, sudden rain, haze days and 19°C office
or classroom aircon, all in the same day.

Shopping has the same problem. Fashion isn't one-size-fits-all: what looks
great on a model or a friend can look completely different on us, because we
all come in different shapes and sizes. Buying clothes online often ends in
disappointment and tedious returns.

This is worth solving because it affects people every day. A better system
helps people get more out of clothes they already own, buy fewer pieces that
don't fit, and send back less, which saves time and money and creates less
waste.

## Solution Overview

SG Wardrobe takes the guesswork out of getting dressed and shopping:

1. People add the clothes they already own to a digital closet, with photos.
2. They enter their body measurements and match their skin shade against an
   on-screen chart.
3. The AI uses the closet, the measurements, the occasion and Singapore's
   conditions to suggest complete outfits from clothes they already have,
   explain their body shape and best colours, and review which pieces suit them.
4. Before buying something online, they paste the shop link. The AI reads the
   product page and size chart and says which size to buy, how it will fit, and
   how well it matches their wardrobe.

Each person's closet, photos and measurements are saved to their own account,
so they can come back on any device.

## Key Features

- **Digital closet:** add clothes with photos (the background is removed in the
  browser), category, colour, fabric, breathability, formality, and whether a
  piece is rain-safe or works as an aircon layer.
- **Weather-aware outfit ideas:** complete outfits (top and bottom or a dress,
  shoes, and optionally a layer and accessories) for preset occasions (Work fit,
  Classroom comfy, Outdoors) or any occasion the user types in, such as "Wedding
  lunch" or "Beach day at Sentosa".
- **Live weather and haze:** the Today page shows Singapore's current
  temperature, feels-like temperature, humidity, the 2-hour and 24-hour
  forecasts, and the PSI and PM2.5 haze readings, all from the official
  Meteorological Service Singapore / National Environment Agency feeds. Outfit
  suggestions are generated for these real conditions (for example rain-safe
  shoes when showers are forecast).
- **Body shape and colour analysis:** from measurements and skin shade, the AI
  identifies body shape (hourglass, pear, inverted triangle, rectangle or apple)
  and suggests flattering colours, colours to avoid, and cuts and silhouettes.
- **Wardrobe review:** "What stays, what goes": each piece is checked against
  the user's measurements and the heat.
- **Smart shopping link analyzer:** paste a link to a specific product (or paste
  a size chart instead) to get the size to buy, a fit check by body area
  (good / snug / loose) and a wardrobe match score, with pieces from the closet
  it pairs with.
- **Accounts:** each person has their own saved closet, measurements and
  review. There is also a sample closet for demo accounts and a feedback form in
  Settings.

## AI Integration

All AI features use **Claude Sonnet 5.5** (Anthropic). The browser never talks
to Anthropic directly: it sends a request to a Python serverless function on
Vercel (`api/style.py`), which holds the API key and forwards the request.

| Feature | What is sent to the AI | What comes back |
|---|---|---|
| Outfit ideas | The occasion and its dress-code rules, live conditions (temperature, feels-like, humidity, 2-hour and 24-hour forecast, haze), the outfits already on screen, and the closet list (name, category, colour, fabric, breathability, formality, rain-safe, aircon layer) | Outfits as JSON, each listing closet item IDs and a short reason |
| Body shape & colours | Height, shoulder, bust, waist, hips, leg length, weight, frame and the chosen skin shade | Body shape, flattering colours, colours to avoid, and recommended cuts |
| Wardrobe review | Measurements and the closet list | Which pieces to keep or let go, and why |
| Shopping link analyzer | Product name, details and size chart read from the shop page (`api/product.py`), plus measurements and the closet list | Recommended size, confidence, fit by body area, match score, and closet pieces it pairs with |

The AI only ever returns text. The app never shows that text as-is: it checks
every answer before displaying it (see **Guardrails** below). When no API key
is set, the app runs with AI switched off and every other feature keeps working.

When run locally with `wardrobe-server.py`, the same prompts go to the Claude
Code CLI installed on that computer instead of the API.

## External Tools & Datasets

| Tool / dataset | Used for |
|---|---|
| [Anthropic Claude API](https://docs.anthropic.com/), model `claude-sonnet-5-5`, through the `anthropic` Python SDK | Outfit ideas, body shape and colour analysis, wardrobe review, size and fit checks |
| [Supabase](https://supabase.com/) (`@supabase/supabase-js`) | Accounts and sign-in, the database for closets, measurements and feedback, and private photo storage |
| [data.gov.sg real-time API](https://data.gov.sg/) (Meteorological Service Singapore / NEA): air temperature, relative humidity, 2-hour and 24-hour forecasts, PSI and PM2.5 | Live weather and haze on the Today page and in outfit prompts. Free and needs no API key |
| [@imgly/background-removal](https://www.npmjs.com/package/@imgly/background-removal) | Removing photo backgrounds in the browser, so the original photo is never uploaded for this |
| [Vercel](https://vercel.com/) | Hosting the web page and the Python serverless functions |
| Google Fonts | Fonts |
| Claude Code (in VS Code) | Building the app; also the local AI backend for `wardrobe-server.py` |
| Gemini | Testing early ideas, user flows and styling logic during planning |
| GitHub | Version control |

The app does not use any training dataset. The sample closet photos in
`assets/` are bundled demo images.

## Installation & Setup

### Prerequisites

- Python 3.10 or newer
- A free [Supabase](https://supabase.com/) project
- For AI locally, either [Claude Code](https://claude.com/claude-code)
  installed and signed in, or an Anthropic API key with credits
  ([console.anthropic.com](https://console.anthropic.com/))

### 1. Get the code

```bash
git clone https://github.com/homesickpencil/sg-wardrobe.git
cd sg-wardrobe
```

### 2. Set up Supabase

1. In the Supabase SQL Editor, run `supabase/setup.sql`. It creates the tables,
   the private photo bucket, the privacy rules (each person can only reach their
   own rows and photos) and the account-deletion function. It is safe to rerun.
2. Run `supabase/feedback.sql` to create the feedback table. People can send
   feedback but not read it. Read it in Supabase → Table Editor → feedback.
3. Optional: run `supabase/demo-account.sql` (put the demo PIN in the script
   first) so that account keeps the built-in sample closet.
4. In Supabase → Authentication → Sign In / Providers → Email, turn
   **Confirm email** off. Sign-in uses made-up addresses that cannot receive
   email.
5. Put your project URL and publishable key at the top of the "Account" script
   in `index.html` and at the top of `api/style.py` and `api/product.py`, or set
   them as the `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` environment
   variables for the functions. Both values are meant to be public. Never put
   the `service_role` or secret key in the page.

### 3. Run locally

```bash
python3 wardrobe-server.py
```

Open <http://localhost:8765>. This local server sends AI requests to the Claude
Code CLI on your computer, so it needs no API key.

To test the Vercel functions instead, run `pip install -r requirements.txt`,
set `ANTHROPIC_API_KEY` in your shell, and use the Vercel CLI (`vercel dev`).

### 4. Deploy to Vercel (optional)

1. Import the GitHub repository in Vercel.
2. In **Settings → Environment Variables**, add:
   - `ANTHROPIC_API_KEY` (optional): your Anthropic API key. Add it only in
     Vercel, never in `index.html` or Git. Without it, the app runs with AI
     switched off.
   - `ANTHROPIC_MODEL` (optional): leave it unset to use `claude-sonnet-5-5`.
     Requests use Anthropic's automatic fallback (`fallbacks: "default"`), so
     any other model must support that too.
3. Deploy, and redeploy after any change to environment variables.
4. Before sharing publicly, set a spend limit in the Anthropic Console and add
   Vercel Firewall rate limiting for `/api/style` and `/api/product`.

## AI Safety & Limitations

### Risks and limitations

- **Size and fit predictions can be wrong.** They depend on the user measuring
  themselves accurately and on the shop publishing a correct size chart. When
  no chart is found, the AI says so and marks its confidence as low. Treat the
  advice as guidance, not a guarantee.
- **Weather is island-wide, not hyper-local.** Temperature and humidity are
  averaged across NEA's weather stations, and the "feels like" value is a heat
  index calculated from them. Conditions at a particular street can differ. If
  the weather feed cannot be reached, the app says so and the AI falls back to a
  typical Singapore day (about 31°C, humid, chance of showers).
- **Colour analysis is approximate.** Skin shade is matched by eye against a
  screen, and screens and lighting vary.
- **Body shape labels are generalisations.** They describe proportions and are
  not a judgement of anyone's body. The app gives styling suggestions, not
  rules.
- **Personal data is sent to a third party.** Measurements and closet details
  are sent to Anthropic to generate answers. Closet photos are not sent to the
  AI.
- **Demo-grade sign-in.** The PIN (initials plus the last 4 digits of a phone
  number) is easy to guess: anyone who knows someone's initials and number can
  open their closet, and two people with the same PIN share one closet. It must
  be replaced with proper authentication before real users join.
- **Shop pages vary.** Some shops block automated reading or load sizes with
  scripts, so the analyzer may not find the product details. Users can paste a
  size chart instead.
- **Cost.** Every AI request costs money. A public demo without a spend limit
  could run up charges.

### Guardrails implemented

- **AI only for signed-in users.** `api/style.py` and `api/product.py` check
  each request's Supabase sign-in token before doing anything, and reject
  requests from other websites.
- **The API key stays on the server.** It is read from Vercel's environment and
  is never sent to the browser.
- **Request limits.** Prompts are capped at 50,000 characters, AI requests time
  out after 45 seconds, and replies are kept short with low effort.
- **Every AI answer is checked before it is shown.** Outfits must use real items
  from the user's closet and have a valid combination (one top and one bottom or
  one dress, plus shoes; a layer must be marked as an aircon layer). Outfits
  that fail these checks are dropped. Shopping results must have a size and a
  0–100 score, and all AI text is length-limited and shown as plain text, not
  HTML.
- **Heat rules in the prompt.** The prompt tells the AI to judge heat honestly,
  for example no layers, denim, wool, leather or boots for Outdoors, and to
  prefer breathable fabrics.
- **Refusals and errors are handled.** If the AI declines a request, Anthropic
  automatically retries on a fallback model. If it still declines, or the
  service is busy or down, the user sees a clear message and their outfits stay
  unchanged.
- **Safe link reading.** The shop page reader only fetches public `http(s)`
  addresses (also after redirects), never private or local network addresses.
- **Private data.** Supabase row-level security means each person can only read
  their own rows and photos. Photos are stored in a private bucket, signing out
  clears the person's data from the browser, and accounts can be deleted.
- **Spend control.** An Anthropic spend limit is set on the account, and the app
  runs with AI switched off when no key is configured.

### Testing

- Tested the live site with several accounts, checking that each person's
  closet, measurements and review stay separate and persist after signing out
  and back in.
- Tested every AI feature (outfit ideas, body shape and colour analysis,
  wardrobe review and the shopping link analyzer) on both the local server and
  the live Vercel deployment.
- Tested the app with AI switched off (no API key) to confirm the closet,
  measurements and settings still work and the AI buttons show a clear message.
- Tested error cases, including a missing or invalid API key and an account
  with no credits, to confirm the app shows an error instead of breaking.
