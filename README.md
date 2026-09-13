# legal metrology compliance scanner

an ocr-based system for extracting mandatory product label information and assisting with legal metrology compliance checking.

this project is being developed for **smart india hackathon 2026 - problem statement 26034: legal metrology compliance scanner**.

---

## about the project

checking packaged products for mandatory declarations is a repetitive process, especially when a large number of products need to be inspected.

the goal of this project is to automate the first stage of this process.

the system takes a photograph of a product label, extracts the text using ocr, identifies important declarations, and uses the position and context of the text to determine which information belongs to which field.

the current python module focuses on the **ocr and field extraction layer** of the complete system.

---

## current workflow


product label image
        |
     paddleocr
        |
text + confidence + bounding boxes
        |
spatial analysis
        |
candidate text detection
        |
regex based extraction
        |
structured product information


