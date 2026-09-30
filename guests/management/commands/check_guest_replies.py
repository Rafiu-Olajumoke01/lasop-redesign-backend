import email
import imaplib
import logging
from email.header import decode_header

from django.conf import settings
from django.core.management.base import BaseCommand

from guests.models import Guest, GuestMessage

logger = logging.getLogger(__name__)


def decode_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return msg.get_payload(decode=True).decode(charset, errors="replace")


class Command(BaseCommand):
    help = "Checks reply@lasop.net for new guest replies and saves them."

    def handle(self, *args, **options):
        imap = imaplib.IMAP4_SSL(settings.REPLY_EMAIL_HOST, settings.REPLY_EMAIL_IMAP_PORT)
        imap.login(settings.REPLY_EMAIL_HOST_USER, settings.REPLY_EMAIL_HOST_PASSWORD)
        imap.select("INBOX")

        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            self.stdout.write("Could not search inbox.")
            return

        ids = data[0].split()
        saved = 0

        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            to_header = msg.get("To", "") + " " + msg.get("Delivered-To", "")

            guest_id = None
            for token in to_header.replace(",", " ").split():
                if "+" in token and "@" in token:
                    local = token.split("+", 1)[1].split("@", 1)[0]
                    guest_id = "GST-" + local.replace("gst", "").upper()
                    break

            if not guest_id:
                continue

            guest = Guest.objects.filter(guest_id=guest_id).first()
            if not guest:
                logger.warning("No guest found for reply tag %s", guest_id)
                continue

            body = decode_body(msg).strip()
            if body:
                GuestMessage.objects.create(guest=guest, sender=GuestMessage.GUEST, body=body)
                saved += 1

        imap.close()
        imap.logout()
        self.stdout.write(f"Saved {saved} new guest reply(ies).")