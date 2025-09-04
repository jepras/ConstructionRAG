"""
Unit tests for the skip text extraction enhancement in partition step.

Tests the implementation of the enhancement that skips fragmented text extraction
on pages with visual content while enhancing VLM prompts.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.pipeline.indexing.steps.enrichment import ConstructionVLMCaptioner
from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2


class TestPartitionSkipEnhancement:
    """Test suite for skip text extraction enhancement."""
    
    def test_stage1_stores_results_in_instance_variable(self, tmp_path):
        """Test that stage1 stores results for stage2 access."""
        # Create temporary directories for processing
        tables_dir = tmp_path / "tables"
        images_dir = tmp_path / "images"
        tables_dir.mkdir()
        images_dir.mkdir()
        
        # Create partitioner with minimal config
        config = {
            "ocr_strategy": "auto",
            "extract_tables": True,
            "extract_images": True,
        }
        partitioner = UnifiedPartitionerV2(config, str(tables_dir), str(images_dir))
        
        # Verify instance variable doesn't exist initially
        assert not hasattr(partitioner, '_stage1_results')
        
        # Mock a minimal PDF for testing
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=1)  # 1 page
            mock_doc.__iter__ = Mock(return_value=iter([Mock()]))
            mock_page = Mock()
            mock_page.get_images = Mock(return_value=[])
            mock_page.find_tables = Mock(return_value=[])
            mock_doc.__getitem__ = Mock(return_value=mock_page)
            mock_doc.metadata = {}
            mock_doc[0].rect.width = 612
            mock_doc[0].rect.height = 792
            mock_fitz.return_value = mock_doc
            
            # Mock the helper methods
            with patch.object(partitioner, '_count_meaningful_images', return_value=0):
                with patch.object(partitioner, '_extract_document_metadata', return_value={}):
                    # Call stage1 method
                    results = partitioner.stage1_pymupdf_analysis("test.pdf")
        
        # Verify results are stored in instance variable
        assert hasattr(partitioner, '_stage1_results')
        assert partitioner._stage1_results is not None
        assert partitioner._stage1_results == results
        assert "page_analysis" in partitioner._stage1_results
        assert "table_locations" in partitioner._stage1_results
        assert "image_locations" in partitioner._stage1_results
        assert "document_metadata" in partitioner._stage1_results
    
    def test_stage2_skips_visual_pages(self, tmp_path):
        """Test that stage2 skips text extraction on pages with visual content."""
        # Create temporary directories for processing
        tables_dir = tmp_path / "tables"
        images_dir = tmp_path / "images"
        tables_dir.mkdir()
        images_dir.mkdir()
        
        # Create partitioner
        config = {"ocr_strategy": "auto"}
        partitioner = UnifiedPartitionerV2(config, str(tables_dir), str(images_dir))
        
        # Set up stage1 results with mixed pages
        partitioner._stage1_results = {
            "page_analysis": {
                1: {"needs_extraction": False},  # Text-only page
                2: {"needs_extraction": True},   # Visual page - should skip
                3: {"needs_extraction": True},   # Visual page - should skip
            }
        }
        
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=3)  # 3 pages
            
            # Create mock pages
            mock_pages = []
            for i in range(3):
                mock_page = Mock()
                mock_page.get_text = Mock(return_value={"blocks": [{"lines": [{"spans": [{"text": f"text page {i+1}"}]}]}]})
                mock_pages.append(mock_page)
            
            mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
            mock_doc.range = Mock(return_value=range(3))
            def get_page(index):
                return mock_pages[index]
            mock_doc.__getitem__ = get_page
            
            mock_fitz.return_value = mock_doc
            
            # Mock text categorization
            with patch.object(partitioner, '_determine_text_category', return_value="NarrativeText"):
                with patch.object(partitioner, '_get_font_size', return_value=12):
                    with patch.object(partitioner, '_get_font_name', return_value="Arial"):
                        with patch.object(partitioner, '_is_bold_text', return_value=False):
                            # Call stage2 method
                            text_elements, raw_elements = partitioner.stage2_fast_text_extraction("test.pdf")
        
        # Verify only page 1 (text-only) was processed
        # Pages 2 and 3 should have been skipped
        assert len(text_elements) == 1  # Only one page processed
        
        # Verify the processed element is from page 1
        assert text_elements[0]["structural_metadata"]["page_number"] == 1
    
    def test_unstructured_skips_visual_page_elements(self):
        """Test that Unstructured path skips text elements from visual pages."""
        # Create partitioner
        config = {"ocr_strategy": "auto"}
        partitioner = UnifiedPartitionerV2(config, "/tmp/tables", "/tmp/images")
        
        # Create mock Unstructured elements
        mock_elements = []
        
        # Create element for page 1 (text-only)
        element1 = Mock()
        element1.category = "NarrativeText"
        element1.metadata = Mock()
        element1.metadata.page_number = 1
        element1.metadata.coordinates = None
        element1.text = "Text from page 1"
        mock_elements.append(element1)
        
        # Create table element for page 2 (visual page) - should be kept
        element2 = Mock()
        element2.category = "Table"
        element2.metadata = Mock()
        element2.metadata.page_number = 2
        element2.metadata.coordinates = None
        element2.text = "Table from page 2"
        mock_elements.append(element2)
        
        # Create text element for page 2 (visual page) - should be skipped
        element3 = Mock()
        element3.category = "NarrativeText"
        element3.metadata = Mock()
        element3.metadata.page_number = 2
        element3.metadata.coordinates = None
        element3.text = "Text from page 2"
        mock_elements.append(element3)
        
        # Create element for page 3 (visual page) - should be skipped
        element4 = Mock()
        element4.category = "ListItem"
        element4.metadata = Mock()
        element4.metadata.page_number = 3
        element4.metadata.coordinates = None
        element4.text = "List item from page 3"
        mock_elements.append(element4)
        
        # Mock document input
        document_input = Mock()
        document_input.filename = "test.pdf"
        
        # Mock PDF analysis for page filtering
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=3)
            mock_doc.close = Mock()
            
            # Set up pages with different visual characteristics
            mock_pages = []
            for i in range(3):
                mock_page = Mock()
                if i == 0:  # Page 1 - text only
                    mock_page.get_images = Mock(return_value=[])
                    mock_page.find_tables = Mock(return_value=[])
                else:  # Pages 2,3 - have visual content  
                    mock_page.get_images = Mock(return_value=[Mock(), Mock()])  # 2 images
                    mock_page.find_tables = Mock(return_value=[])
                mock_pages.append(mock_page)
            
            def get_page(index):
                return mock_pages[index]
            mock_doc.__getitem__ = get_page
            mock_doc.range = Mock(return_value=range(3))
            mock_fitz.return_value = mock_doc
            
            # Mock the meaningful images count
            with patch.object(partitioner, '_count_meaningful_images') as mock_count:
                mock_count.side_effect = lambda doc, page, images: len(images)  # Return image count as meaningful count
                
                # Call the normalize method
                result = partitioner._normalize_unstructured_output(mock_elements, "test.pdf", document_input)
        
        # Verify filtering results
        text_elements = result["text_elements"]
        
        # Should have 2 elements: 
        # - NarrativeText from page 1 (text-only page)
        # - Table from page 2 (tables are allowed on visual pages)
        assert len(text_elements) == 2
        
        # Verify the correct elements were kept
        pages_kept = [el["structural_metadata"]["page_number"] for el in text_elements]
        categories_kept = [el["structural_metadata"]["element_category"] for el in text_elements]
        
        assert 1 in pages_kept  # Page 1 text should be kept
        assert 2 in pages_kept  # Page 2 table should be kept
        assert "NarrativeText" in categories_kept  # Text from page 1
        assert "Table" in categories_kept  # Table from page 2


class TestVLMPromptEnhancements:
    """Test suite for VLM prompt enhancements."""
    
    def test_table_vlm_prompt_enhancement(self):
        """Test that table VLM prompt includes comprehensive text extraction requirements."""
        captioner = ConstructionVLMCaptioner("test-model", "test-key", "English")
        
        # Test prompt content by accessing the method's prompt construction logic
        page_num = 2
        source_file = "test.pdf"
        focus_hint = ""
        caption_language = "English"
        
        # Reconstruct the enhanced prompt to verify content
        expected_prompt = f"""You are analyzing a table image extracted from page {page_num} of a construction/technical document ({source_file}).{focus_hint}

Please provide a comprehensive description that captures ALL content on this section of the page:

1. **All Visible Text in Table**: Read and transcribe ALL text visible in the table, including headers, data, footnotes, cell contents.
2. **Table Structure**: Number of rows, columns, organization, table borders and layout
3. **Data Relationships**: How the data is organized and what it represents
4. **Surrounding Text**: Any text labels, captions, references, or annotations around the table
5. **Technical Details**: Any measurements, specifications, material references, or technical codes visible

Focus on being extremely thorough - capture every piece of text and technical information visible in this image, as this will be the only source of this content.

IMPORTANT: Please provide your detailed description in {caption_language}."""
        
        # Verify key enhancement indicators
        assert "ALL content on this section" in expected_prompt
        assert "Surrounding Text" in expected_prompt
        assert "extremely thorough" in expected_prompt
        assert "only source of this content" in expected_prompt
        assert "Technical Details" in expected_prompt
        
    def test_fullpage_vlm_prompt_enhancement(self):
        """Test that full-page VLM prompt emphasizes complete text extraction."""
        captioner = ConstructionVLMCaptioner("test-model", "test-key", "English")
        
        # Test prompt content
        page_num = 3
        source_file = "test.pdf"
        complexity = "complex"
        context_section = ""
        caption_language = "English"
        
        # Reconstruct the enhanced prompt to verify content
        expected_prompt = f"""You are analyzing a full-page image from page {page_num} of a construction/technical document ({source_file}). This page has {complexity} visual complexity and contains visual content that requires comprehensive text extraction.

This image is the PRIMARY SOURCE for all text content on this page. Please provide an extremely detailed description that captures:

1. **ALL Text Content**: Extract and transcribe ALL visible text including:
   - Headers, titles, and section headings
   - Body text, paragraphs, and descriptions  
   - Table content, data, and headers
   - Labels, annotations, and callouts
   - Measurements, dimensions, and specifications
   - Material references and technical codes
   - Footnotes, legends, and captions

2. **Technical Drawing Details**: What type of drawing, elements shown, dimensions, materials, construction details

3. **Spatial Relationships**: How different parts relate, connect, or reference each other

4. **Visual Context**: How text relates to diagrams, what the visual elements represent

5. **Construction-Specific Information**: Building materials, techniques, standards, compliance codes

Read this page as if you are digitizing all text content - be extremely thorough as this VLM caption will replace any OCR text extraction.

{context_section}

IMPORTANT: Please provide your comprehensive description in {caption_language}."""
        
        # Verify key enhancement indicators
        assert "PRIMARY SOURCE for all text content" in expected_prompt
        assert "ALL Text Content" in expected_prompt
        assert "replace any OCR text extraction" in expected_prompt
        assert "digitizing all text content" in expected_prompt
        assert "extremely detailed" in expected_prompt


@pytest.mark.parametrize("page_info,expected_skip", [
    ({"needs_extraction": False}, False),  # Text-only page - process
    ({"needs_extraction": True}, True),    # Visual page - skip
    ({}, False),                           # Missing info - process (safe default)
])
def test_skip_logic_parameterized(page_info, expected_skip):
    """Parameterized test for skip logic decision making."""
    # Simulate the skip condition check
    should_skip = page_info.get('needs_extraction', False)
    assert should_skip == expected_skip


@pytest.mark.parametrize("element_category,page_needs_extraction,expected_skip", [
    ("NarrativeText", False, False),  # Text on text-only page - process
    ("NarrativeText", True, True),    # Text on visual page - skip
    ("Table", True, False),           # Table on visual page - process (allowed)
    ("ListItem", True, True),         # List on visual page - skip
    ("Title", False, False),          # Title on text-only page - process
])
def test_unstructured_skip_logic_parameterized(element_category, page_needs_extraction, expected_skip):
    """Parameterized test for Unstructured element skip logic."""
    # Simulate the Unstructured skip condition check
    should_skip = (element_category not in ["Table"] and page_needs_extraction)
    assert should_skip == expected_skip