# Step Into Dev Blog

Hugo-powered blog deployed to Azure Static Web Apps at [stepinto.dev](https://stepinto.dev).

## Local Development

### Prerequisites

- [Hugo](https://gohugo.io/installation/) (v0.116.0 or later)
- Git

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd mcp-blogs

# Init the theme submodule
git submodule update --init --recursive

# Start the dev server
hugo server -D
```

The site will be available at http://localhost:1313

### Adding the theme manually (if submodule wasn't cloned)

```bash
git submodule add https://github.com/panr/hugo-theme-terminal.git themes/terminal
```

## Creating Posts

```bash
hugo new posts/my-new-post.md
```

Posts live in `content/posts/`. Set `draft = false` when ready to publish.

## Building for Production

```bash
hugo --minify
```

Output goes to `public/`.

## Deployment

Deployment is handled automatically via GitHub Actions on push to `main`. See `.github/workflows/deploy.yml`.

### Infrastructure

Azure infrastructure is defined in Bicep. See [infra/README.md](infra/README.md) for deployment instructions.

### DNS

Domain is managed in DNSimple. See infra README for DNS configuration steps.

## License

Content is copyright Andy Cross. Code/config is MIT.

