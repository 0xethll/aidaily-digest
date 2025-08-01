## Get bot info then assign an ENV variable that stores the bot info

```
https://api.telegram.org/bot<BOT_TOKEN>/getMe
```

```
# wrangler.jsonc
"vars": {
    "BOT_INFO": {
        "id": 8277848906,
        "is_bot": true,
        "first_name": "aidaily-digest",
        "username": "aidaily_digest_bot",
        "can_join_groups": true,
        "can_read_all_group_messages": false,
        "supports_inline_queries": false,
        "can_connect_to_business": false,
        "has_main_web_app": false
    }
}
```

## Add a secret to your project

```
pnpx wrangler secret put BOT_TOKEN
```

- In loacl development, create a `.dev.vars` file in the root of your project to define secrets:

```
BOT_TOKEN=<your_bot_token>  # <- replace this with your bot token.
```

## Start a dev server

```
pnpm run dev
```

## Use cloudflared reverse proxy service

### Install cloudflared

```
brew install cloudflared
```

### Add Your Domain to Cloudflare

1. Go to Cloudflare and log into your account (create one if you don’t have one).
2. Click "Add a Site", enter your domain (e.g., example.com), and click "Add site".
3. Choose your preferred plan. For most developers, the Free Plan is sufficient.
4. Cloudflare will scan for your existing DNS records. Wait for the scan and review your DNS settings for accuracy.
5. Click "Continue".

### Switch Nameservers at Your Domain Registrar

After Cloudflare scans your DNS, it will provide two or more nameserver addresses.

1. Copy these nameserver addresses.
2. Go to your domain registrar (e.g. Namecheap, GoDaddy, Google Domains).
3. Find the DNS or Nameservers setting page for your domain.
4. Change the existing nameservers to the ones provided by Cloudflare.
5. Save your changes.
   Changes may take up to 24 hours to propagate globally, but often update in 1-2 hours.
6. Return to the Cloudflare dashboard. Once Cloudflare detects the correct nameservers, your site will go "Active".

### Authenticate cloudflared

```
cloudflared tunnel login
```

After successful authentication, cloudflared will save your credential in `/Users/WHO/.cloudflared/cert.pem`.

### Create a Cloudflare Tunnel

```
cloudflared tunnel create aidaily-digest/<YOUR_TUNNEL_NAME>
```

- Tunnel credentials written to /Users/WHO/.cloudflared/54a6f1f1-f87c-4371-bced-b8c89b47239b.json. To revoke these credentials, delete the tunnel.

- This command will generate a unique UUID for your tunnel, which you'll need later.

- Confirm that the tunnel has been successfully created by running:
  ```
  cloudflared tunnel list
  ```

### Create a configuration file

In your .cloudflared directory, create a config.yml file using any text editor. This file will configure the tunnel to route traffic from a given origin to the hostname of your choice.

```
touch ~/.cloudflared/config.yml
```

Add the following fields to the file:

```
url: http://localhost:8787
tunnel: <Tunnel-UUID>
credentials-file: /root/.cloudflared/<Tunnel-UUID>.json
```

### Start routing traffic

```
-- `cloudflared tunnel route dns <UUID or NAME> <hostname>`

cloudflared tunnel route dns 54a6f1f1-f87c-4371-bced-b8c89b47239b aidailydigest

2025-08-01T01:31:22Z INF Added CNAME aidailydigest.mondungeons.xyz which will route to this tunnel tunnelID=54a6f1f1-f87c-4371-bced-b8c89b47239b
```

### Run the tunnel

```
cloudflared tunnel run 54a6f1f1-f87c-4371-bced-b8c89b47239b/<UUID or NAME>
```

If your configuration file has a custom name or is not in the .cloudflared directory, add the --config flag and specify the path.

```
cloudflared tunnel --config /path/your-config-file.yml run <UUID or NAME>

```

### Check the tunnel

```
cloudflared tunnel info <UUID or NAME>
```

## Setting webhook

We need to tell Telegram where to send updates to. Open your browser and visit this URL:

```
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<MY_BOT>.<MY_SUBDOMAIN>.workers.dev/
```

For local development:

```
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://aidailydigest.mondungeons.xyz
```

## Delete webhook

```
https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook
```
