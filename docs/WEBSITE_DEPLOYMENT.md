# Website Deployment

The public landing page is a static React/Vite application in
`apps/website/`. It is deployed independently from the desktop application;
Firebase Hosting serves only the generated `apps/website/dist/` directory.

## Hosting Choice

Use **Firebase Hosting**, not Firebase App Hosting. The website has no server
rendering or backend runtime: it is a static single-page application with
hashed Vite assets, so Hosting is the simpler and appropriate product.

`firebase.json` is committed at the repository root. It sets the deploy root,
long-lived cache headers for hashed assets, and `no-cache` for `index.html`.
The project association file `.firebaserc` is intentionally local and ignored:
this repository can be cloned and previewed without binding it to one Firebase
project.

## One-Time Setup

1. Create a Firebase project in the Firebase Console, with a globally unique
   project ID such as `optees-app` if it is available.
2. Install and authenticate the Firebase CLI. The current local environment
   already provides the `firebase` command.
3. From the repository root, associate the local checkout with the project:

   ```bash
   firebase login
   firebase use --add
   ```

   Select the new project and use the alias `production`. This writes the
   ignored `.firebaserc` file locally.

4. Copy `apps/website/.env.example` to `apps/website/.env.local` and set the
   exact canonical URL that Firebase assigned, for example:

   ```bash
   VITE_SITE_URL=https://optees-app.web.app
   ```

   The build replaces `%SITE_URL%` in canonical, Open Graph, Twitter, robots,
   sitemap, and `llms.txt` metadata. Do this before the first public deploy and
   again when moving to a custom domain.

## Preview And Production Deploys

Build first, then use a Firebase preview channel before publishing:

```bash
npm --prefix apps/website run build
firebase hosting:channel:deploy preview --expires 7d
```

After checking the generated preview URL, publish the same local build:

```bash
firebase deploy --only hosting
```

The Firebase CLI automatically serves the `public` directory configured in
`firebase.json`. Do not deploy `apps/website/` itself or `node_modules/`.

## Release Checklist

1. Regenerate the application screenshots when a released desktop flow changes:

   ```bash
   PYTHONPATH=src /opt/anaconda3/envs/optees/bin/python \
     apps/website/scripts/capture_app_screenshots.py
   ```

2. Build with the production `VITE_SITE_URL` configured.
3. Open the preview on desktop and mobile widths; validate language switching,
   release download links, images, and canonical metadata.
4. Deploy production only after the desktop release has been published on
   GitHub Releases, so the landing page cannot promise an unavailable build.

## Continuous Deployment From Landing Tags

`.github/workflows/deploy-website.yml` deploys the live Firebase Hosting site
only when a tag matching `landing-vMAJOR.MINOR.PATCH` is pushed. It is separate
from `vMAJOR.MINOR.PATCH`, which continues to build desktop release artifacts.

The workflow:

1. checks out the exact tagged commit and validates the tag format;
2. installs dependencies from `apps/website/package-lock.json` with `npm ci`;
3. builds with `VITE_SITE_URL=https://optees-1acac.web.app`;
4. deploys `apps/website/dist/` to Firebase Hosting's `live` channel.

### Required GitHub Secret

Before pushing the first landing tag, create a repository Actions secret named
`FIREBASE_SERVICE_ACCOUNT_OPTEES_1ACAC`. Its value must be the full JSON key
for a Firebase/Google Cloud service account allowed to deploy Firebase
Hosting. Never commit this JSON file or put it in an Actions variable.

The Firebase CLI command `firebase init hosting:github` can create this
service account and repository secret automatically, but it also generates
its own workflow files. For this repository, keep the custom tag workflow and
either use the generated secret or create the service account manually. At a
minimum, grant its identity Firebase Hosting deployment permissions; use the
roles recommended by the official Firebase Hosting GitHub Action when the
project later adds Authentication preview domains or Cloud Run rewrites.

Add the secret in GitHub under **Settings -> Secrets and variables -> Actions
-> New repository secret**. The secret name in the workflow is deliberately
specific to the Firebase Project ID, so it cannot accidentally target another
project.

### Publish A Landing Release

From the repository root, first publish the commits the tag must represent:

```bash
git push
git tag -a landing-v0.0.1 -m "Publish landing v0.0.1"
git push origin landing-v0.0.1
```

No Python application version bump is needed for a `landing-v*` tag. GitHub
Actions deploys the website source present at that exact tag; check the
**Deploy Website** workflow run and open `https://optees-1acac.web.app` when
it succeeds.
