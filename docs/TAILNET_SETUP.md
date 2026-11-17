# Putting Wisp on the tailnet

Wisp joins your Tailscale tailnet itself (TailTiny, inside the firmware) and reaches Hermes on
the Mac at its tailnet address, from home Wi-Fi, a work network or a phone hotspot alike.
Nothing on the Mac is published to the internet. The Mac's address and the auth key live only in
`config/wisp.local.json` (git-ignored) and on the board, never in this repo.

Checked 2026-11-16: the Mac (`the-mac`) is on the tailnet, and Hermes's gadget port
already answers on its tailnet address, so **nothing changes on the Mac**.

## 1. Access rules (Tailscale admin console → Access controls)

Merge these into your policy, with the Mac's tailnet address (`tailscale ip -4` on the Mac, or
`hermes_url_away` in the local config) in place of `MAC_TAILNET_IP`:

```json
{
  "tagOwners": {
    "tag:wisp": ["autogroup:admin"]
  },
  "grants": [
    {"src": ["tag:wisp"], "dst": ["MAC_TAILNET_IP"], "ip": ["tcp:8765"]}
  ]
}
```

**Check the default rule.** A new tailnet's policy allows everything to everything
(`"src": ["*"], "dst": ["*"]`, as a grant or an `acls` entry). While that rule is there, Wisp
can reach every machine, not only the gadget port. To limit it, change that rule's `src` from
`"*"` to `"autogroup:member"`: your own devices keep full access, and tagged devices (Wisp)
get only what the grant above allows.

## 2. Auth key (Settings → Keys → Generate auth key)

- **Reusable:** off (one key, one Wisp)
- **Ephemeral:** off (or she leaves the tailnet whenever she powers off)
- **Pre-approved:** on
- **Tags:** `tag:wisp`

Copy the key (`tskey-auth-…`). It's a secret; it's spent once Wisp joins. Tagged devices don't
expire, so no key-expiry step is needed.

## 3. Give it to Wisp (USB)

With the board on USB:

```text
python tools/set_tailnet.py COM3
```

It asks for the key at a hidden prompt and sends it to the board with the Mac's tailnet
address and `tailnet on`. The key is never printed or saved. On the screen: *Joining tailnet*,
then *Reaching Hermes over the tailnet*, then she's back.

## 4. Checks

1. **At home:** Ready again; `diag` shows `tailnet` up, `hermes.path` `direct`.
2. **Away:** on a phone hotspot, a voice turn gets a spoken reply (path often `relay`).
3. **Back home:** she reconnects without a restart.
4. **Restart:** she rejoins without a new key.
5. **Memory and battery:** free internal RAM in `diag`; the idle ladder's screen-off doze still
   happens.

## Undo

`set tailnet off` (the board restarts and connects straight to `server`; set it back to the home
address). If Wisp is lost: admin console → Machines → Wisp → Remove.
