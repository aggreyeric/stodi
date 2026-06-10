"""Stodi core — the channel-agnostic brain.

Channels (Telegram, web/Quasar, WhatsApp, CLI) are thin adapters over this.
They normalize input, call `service.handle_message(...)`, and render the
reply. No agent logic lives in a channel.
"""
