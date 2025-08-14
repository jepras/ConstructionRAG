import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'

test.describe('Upload Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3002/upload')
  })

  test('should display upload page with all elements', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText('Index your first project')
    
    // Check dropzone is visible
    await expect(page.locator('text=Click to upload or drag and drop')).toBeVisible()
    
    // Check email input exists
    await expect(page.locator('input[type="email"]')).toBeVisible()
    
    // Check visibility toggles
    await expect(page.locator('text=Public')).toBeVisible()
    await expect(page.locator('text=Private')).toBeVisible()
    
    // Check data privacy toggles
    await expect(page.locator('text=Share with External AI')).toBeVisible()
    await expect(page.locator('text=Keep Data Private')).toBeVisible()
    
    // Check expert modules section
    await expect(page.locator('text=Expert Modules')).toBeVisible()
    
    // Check Index Repository button
    await expect(page.locator('button:has-text("Index Repository")')).toBeVisible()
  })

  test('should handle file upload and show progress', async ({ page }) => {
    // Create a test PDF file
    const testPdfPath = path.join(__dirname, 'test-document.pdf')
    
    // Create a minimal PDF for testing if it doesn't exist
    if (!fs.existsSync(testPdfPath)) {
      const PDFDocument = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000274 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n362\n%%EOF'
      fs.writeFileSync(testPdfPath, PDFDocument)
    }

    // Upload file using file input
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(testPdfPath)
    
    // Verify file appears in selected files list
    await expect(page.locator('text=test-document.pdf')).toBeVisible()
    await expect(page.locator('text=Selected files (1/5)')).toBeVisible()
    
    // Enter email
    await page.fill('input[type="email"]', 'test@example.com')
    
    // Mock API response for upload
    await page.route('**/api/uploads', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          indexing_run_id: 'test-run-123',
          message: 'Upload successful'
        })
      })
    })

    // Mock API response for progress checking
    await page.route('**/api/indexing-runs/test-run-123/progress', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          current_step: 'Completed',
          progress_percentage: 100,
          documents_processed: 1,
          total_documents: 1
        })
      })
    })
    
    // Click Index Repository button
    await page.click('button:has-text("Index Repository")')
    
    // Should show indexing progress
    await expect(page.locator('text=Indexing Ongoing...')).toBeVisible({ timeout: 5000 })
    
    // Should eventually show success message
    await expect(page.locator('text=We are on it!')).toBeVisible({ timeout: 10000 })
    
    // Clean up test file
    if (fs.existsSync(testPdfPath)) {
      fs.unlinkSync(testPdfPath)
    }
  })

  test('should validate email before upload', async ({ page }) => {
    // Create test PDF
    const testPdfPath = path.join(__dirname, 'test-document.pdf')
    if (!fs.existsSync(testPdfPath)) {
      const PDFDocument = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000274 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n362\n%%EOF'
      fs.writeFileSync(testPdfPath, PDFDocument)
    }

    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(testPdfPath)
    
    // Try to submit without email
    await page.click('button:has-text("Index Repository")')
    
    // Should show error
    await expect(page.locator('text=Please enter a valid email address')).toBeVisible()
    
    // Clean up
    if (fs.existsSync(testPdfPath)) {
      fs.unlinkSync(testPdfPath)
    }
  })

  test('should toggle visibility and privacy options', async ({ page }) => {
    // Check Public is selected by default
    const publicButton = page.locator('button:has-text("Public")').first()
    await expect(publicButton).toHaveClass(/bg-primary/)
    
    // Click Private
    const privateButton = page.locator('button:has-text("Private")').first()
    await privateButton.click()
    await expect(privateButton).toHaveClass(/bg-primary/)
    await expect(publicButton).not.toHaveClass(/bg-primary/)
    
    // Toggle data privacy options
    const keepPrivateButton = page.locator('button:has-text("Keep Data Private")')
    await keepPrivateButton.click()
    await expect(keepPrivateButton).toHaveClass(/bg-primary/)
  })
})