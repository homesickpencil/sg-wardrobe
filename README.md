# Singapore Wardrobe App

This is a static, mobile-friendly wardrobe app with server-backed AI styling and
shopping checks. User closet items and profile information stay in that user's
browser storage. AI requests send the information needed for the requested
styling task to Anthropic; the Anthropic API key stays on the server.

## Deploy as a public Vercel webpage

1. Put this folder in a GitHub repository and import that repository in Vercel.
   Set the Vercel project **Root Directory** to this folder.
2. In Vercel, open **Settings → Environment Variables** and add:
   - `ANTHROPIC_API_KEY`: your Anthropic API key. Add it only in Vercel; never
     put it in `index.html` or commit it to Git.
   - `ANTHROPIC_MODEL`: `claude-sonnet-4-20250514`, or another model enabled for
     your Anthropic account.
3. Deploy (or redeploy after adding/changing environment variables). Share the
   resulting Vercel URL; visitors should open that URL, not the local HTML file.
4. Before sharing the demo publicly, set an appropriate Anthropic spend limit
   and configure Vercel Firewall rate limiting for `/api/style` to help prevent
   unexpected API usage.

Vercel serves `index.html` and the item photos as static files. The Python
functions in `api/` handle AI styling and the shopping page lookup. The API key
is read from the server environment and is never sent to the browser.

## Accounts and storage (Supabase)

People sign in with a PIN: their initials plus the last 4 digits of their phone
number (for example SL1234). The app turns the PIN into a made-up email address
(`sl1234@pin.wardrobe.invalid`) and password for Supabase, so no email is ever
sent. Their closet, measurements and review are saved to the Supabase project,
with item photos in a private storage bucket. Signing out clears that person's
data from the browser.

The PIN is for demos and testing only: anyone who knows someone's initials and
phone number can open their closet, and two people with the same PIN share one
closet. Switch back to email sign-in (or real passwords) before real users.

- The project URL and publishable key are at the top of the "Account" script in
  `index.html`. Both are meant to be public; never put the `service_role` or
  secret key in the page.
- Everyone signs in from the welcome screen. New accounts start with an empty
  closet and a "Get started" card; accounts marked `demo` in `user_state` keep
  the built-in sample closet instead. `supabase/demo-account.sql` adds that
  column and marks the demo account (put its PIN in the script).
- `supabase/setup.sql` creates the tables, the photo bucket, the privacy rules
  (each person can only reach their own rows and photos) and the account
  deletion function. Run it in the Supabase SQL Editor; it is safe to rerun.
- `supabase/feedback.sql` creates the table behind the Settings page's feedback
  form. People can send feedback but not read it; read it in Supabase → Table
  Editor → feedback.
- In Supabase → Authentication → Sign In / Providers → Email, "Confirm email"
  must be off, or new PINs cannot create a closet (the made-up addresses cannot
  receive a confirmation email).

## Run locally

The local server continues to use the Claude CLI available on this computer:

```bash
python3 wardrobe-server.py
```

Then open <http://localhost:8765>. The CLI-based local workflow does not need an
Anthropic API key. To test the Vercel functions locally, install the packages
from `requirements.txt`, set `ANTHROPIC_API_KEY` in your shell, and use the
Vercel CLI.
