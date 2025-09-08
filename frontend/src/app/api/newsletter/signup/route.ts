import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json(
        { error: "Email is required" },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: "Please enter a valid email address" },
        { status: 400 }
      );
    }

    // Call Loops API to create contact
    const loopsApiKey = process.env.LOOPS_API_KEY;
    
    if (!loopsApiKey) {
      console.error("LOOPS_API_KEY not configured");
      return NextResponse.json(
        { error: "Newsletter service not configured" },
        { status: 500 }
      );
    }

    const loopsResponse = await fetch("https://app.loops.so/api/v1/contacts/create", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${loopsApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        source: "Website Footer",
        subscribed: true,
        userGroup: "Newsletter Subscribers",
      }),
    });

    const loopsData = await loopsResponse.json();

    if (!loopsResponse.ok) {
      console.error("Loops API error:", loopsData);
      
      // Check if user already exists
      if (loopsData.message?.includes("already in your audience") || 
          loopsData.message?.includes("already exists") || 
          loopsData.error?.includes("already exists")) {
        return NextResponse.json(
          { success: true, message: "You're already subscribed!" },
          { status: 200 }
        );
      }
      
      return NextResponse.json(
        { error: "Failed to subscribe. Please try again." },
        { status: 500 }
      );
    }

    // Send confirmation email
    try {
      const { sendNewsletterConfirmation } = await import("@/lib/loops");
      const confirmationResult = await sendNewsletterConfirmation(email);
      
      if (!confirmationResult.success) {
        console.warn(`Failed to send confirmation email to ${email}: ${confirmationResult.error}`);
        // Don't fail the signup if confirmation email fails
      }
    } catch (confirmationError) {
      console.warn(`Error sending confirmation email: ${confirmationError}`);
      // Don't fail the signup if confirmation email fails
    }

    // Log successful signup
    console.log(`Newsletter signup successful: ${email}`);

    return NextResponse.json(
      { 
        success: true, 
        message: "Successfully subscribed! Check your email for confirmation." 
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("Newsletter signup error:", error);
    return NextResponse.json(
      { error: "An unexpected error occurred" },
      { status: 500 }
    );
  }
}