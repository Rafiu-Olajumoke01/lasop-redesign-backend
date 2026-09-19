from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
from .models import Assessment


def _label_html(text):
    return (
        f'<p style="margin:0 0 4px; color:#111827; font-size:13px; font-weight:600; '
        f'text-transform:uppercase; letter-spacing:0.5px;">{escape(text)}</p>'
    )


def _plain_section_html(title, body):
    """A simple label + text block (used for 'Assessed on')."""
    return f"""
                    {_label_html(title)}
                    <p style="margin:0 0 20px; color:#374151; font-size:15px; line-height:1.6;">{linebreaksbr(body)}</p>
    """


def _boxed_section_html(title, blocks):
    """
    A highlighted block with a blue left border.
    `blocks` is a list of (sub_heading_or_None, text) tuples.
    """
    inner = ""
    for sub_heading, text in blocks:
        if sub_heading:
            inner += (
                f'<p style="margin:12px 0 2px; color:#2563eb; font-size:12px; font-weight:700; '
                f'text-transform:uppercase; letter-spacing:0.4px;">{escape(sub_heading)}</p>'
            )
        inner += (
            f'<p style="margin:0; color:#111827; font-size:15px; line-height:1.6;">'
            f'{linebreaksbr(text)}</p>'
        )

    return f"""
                    <table role="presentation" width="100%" style="background-color:#f9fafb; border-left:4px solid #2563eb; border-radius:6px; margin:0 0 20px;">
                      <tr>
                        <td style="padding:16px 20px;">
                          {_label_html(title)}
                          {inner}
                        </td>
                      </tr>
                    </table>
    """


@receiver(post_save, sender=Assessment)
def notify_guardian_of_assessment(sender, instance, created, **kwargs):
    if not created:
        return  # only fire on new assessments, not edits

    student = instance.student
    guardian_email = student.guardian_email

    if not guardian_email:
        return  # nothing to send to — silently skip

    student_name = f"{student.first_name} {student.last_name}".strip() or student.email
    tutor_name = f"{instance.author.first_name} {instance.author.last_name}".strip() or instance.author.email
    guardian_name = student.guardian_name or "Guardian"
    date_str = instance.created_at.strftime("%d %B %Y")

    # Current cohort name (same lookup pattern as AssessmentSerializer)
    app = student.applications.filter(cohort__isnull=False).order_by('-created_at').first()
    cohort_name = app.cohort.name if app else None

    if cohort_name:
        tutor_intro = f"{tutor_name}, the tutor for {cohort_name},"
    else:
        tutor_intro = f"{tutor_name}"

    # ------------------------------------------------------------------
    # Content for the three sections.
    # NOTE: adjust these field names if your Assessment model uses
    # different ones. Missing/empty fields are simply left out of the email.
    # ------------------------------------------------------------------
    assessed_on = str(instance.assessed_on) if instance.assessed_on else ""
    observation = getattr(instance, "tutor_observation", "") or ""
    recommendations = getattr(instance, "tutor_recommendations", "") or ""
    tutor_response = getattr(instance, "tutor_response", "") or ""

    # Convert the 1-5 rating into a percentage score, e.g. 4 -> 80%
    rating_percent = instance.rating * 20 if instance.rating else None

    # ------------------------------------------------------------------
    # Rating badge (HTML)
    # ------------------------------------------------------------------
    rating_html = ""
    if rating_percent:
        if rating_percent >= 80:
            badge_bg, badge_text, badge_border = "#ecfdf5", "#059669", "#a7f3d0"
        elif rating_percent >= 50:
            badge_bg, badge_text, badge_border = "#fffbeb", "#d97706", "#fde68a"
        else:
            badge_bg, badge_text, badge_border = "#fef2f2", "#dc2626", "#fecaca"

        rating_html = f"""
                    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">
                      <tr>
                        <td style="background-color:{badge_bg}; border:1px solid {badge_border}; border-radius:999px; padding:6px 16px;">
                          <span style="color:{badge_text}; font-size:14px; font-weight:700; letter-spacing:0.2px;">{rating_percent}%</span>
                          <span style="color:{badge_text}; font-size:11px; font-weight:600; opacity:0.75; text-transform:uppercase; letter-spacing:0.4px; margin-left:4px;">Performance Score</span>
                        </td>
                      </tr>
                    </table>
        """

    # ------------------------------------------------------------------
    # Section 1: Assessed on
    # ------------------------------------------------------------------
    assessed_on_html = _plain_section_html("Assessed on", assessed_on) if assessed_on else ""
    assessed_on_text = f"ASSESSED ON\n{assessed_on}\n\n" if assessed_on else ""

    # ------------------------------------------------------------------
    # Section 2: Tutor's observations and recommendations
    # ------------------------------------------------------------------
    obs_blocks = []
    if observation:
        obs_blocks.append(("Observations", observation))
    if recommendations:
        obs_blocks.append(("Recommendations", recommendations))

    observations_html = (
        _boxed_section_html("Tutor's Observations & Recommendations", obs_blocks)
        if obs_blocks else ""
    )
    observations_text = ""
    if obs_blocks:
        observations_text = "TUTOR'S OBSERVATIONS & RECOMMENDATIONS\n"
        for sub_heading, text in obs_blocks:
            observations_text += f"{sub_heading}: {text}\n"
        observations_text += "\n"

    # ------------------------------------------------------------------
    # Section 3: Tutor's response
    # ------------------------------------------------------------------
    response_html = (
        _boxed_section_html("Tutor's Response", [(None, tutor_response)])
        if tutor_response else ""
    )
    response_text = f"TUTOR'S RESPONSE\n{tutor_response}\n\n" if tutor_response else ""

    rating_text = f"PERFORMANCE SCORE\n{rating_percent}%\n\n" if rating_percent else ""

    subject = f"New Assessment for {student_name}"

    # Plain text fallback (for email clients that don't render HTML)
    text_body = (
        f"Hi {guardian_name},\n\n"
        f"{tutor_intro} just posted a new assessment for {student_name} on {date_str}.\n\n"
        f"{assessed_on_text}"
        f"{observations_text}"
        f"{response_text}"
        f"{rating_text}"
        f"— LASOP"
    )

    # Styled HTML version
    html_body = f"""
    <html>
      <body style="margin:0; padding:0; background-color:#f4f6f8; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f8; padding:32px 16px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" style="max-width:520px; background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">

                <!-- Header -->
                <tr>
                  <td style="background-color:#2563eb; padding:24px 32px;">
                    <span style="color:#ffffff; font-size:20px; font-weight:700; letter-spacing:0.5px;">LASOP</span>
                  </td>
                </tr>

                <!-- Body -->
                <tr>
                  <td style="padding:32px;">
                    <p style="margin:0 0 4px; color:#111827; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">New Assessment</p>
                    <h1 style="margin:0 0 16px; color:#111827; font-size:22px; font-weight:700;">{escape(student_name)}</h1>

                    <p style="margin:0 0 20px; color:#374151; font-size:15px; line-height:1.5;">
                      Hi {escape(guardian_name)}, <strong>{escape(tutor_intro)}</strong> shared a new assessment for {escape(student_name)} on {date_str}.
                    </p>

                    {assessed_on_html}
                    {observations_html}
                    {response_html}
                    {rating_html}

                    <p style="margin:24px 0 0; color:#9ca3af; font-size:13px; line-height:1.5;">
                      This is an automated notification from LASOP. You're receiving this because you're listed as the guardian for {escape(student_name)}.
                    </p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td style="background-color:#f9fafb; padding:16px 32px; text-align:center;">
                    <p style="margin:0; color:#9ca3af; font-size:12px;">&copy; LASOP — Cohort-Based Coding School</p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[guardian_email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)