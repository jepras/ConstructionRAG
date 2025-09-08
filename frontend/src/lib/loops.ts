/**
 * Loops service for newsletter confirmation emails
 */

// Hardcoded template IDs (these are not secrets, just template references)
const NEWSLETTER_CONFIRMATION_TEMPLATE_ID = "cmfb5sk790boz4o0igafcmfm4";

interface LoopsResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export async function sendNewsletterConfirmation(email: string): Promise<LoopsResponse> {
  const loopsApiKey = process.env.LOOPS_API_KEY;

  if (!loopsApiKey) {
    console.error("Loops API key missing");
    return { success: false, error: "Newsletter service not configured" };
  }

  try {
    const response = await fetch("https://app.loops.so/api/v1/transactional", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${loopsApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        transactionalId: NEWSLETTER_CONFIRMATION_TEMPLATE_ID,
        email,
        dataVariables: {
          email,
        },
        addToAudience: true,
        userGroup: "Newsletter Subscribers",
      }),
    });

    const data = await response.json();

    if (response.ok) {
      console.log(`Newsletter confirmation sent to ${email}`);
      return { success: true, message: "Confirmation email sent" };
    } else {
      console.error("Loops confirmation email error:", data);
      return { success: false, error: "Failed to send confirmation email" };
    }
  } catch (error) {
    console.error("Newsletter confirmation error:", error);
    return { success: false, error: "Failed to send confirmation email" };
  }
}