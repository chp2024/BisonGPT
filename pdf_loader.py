import csv
import pdfplumber

file_p = "BisonGPT/Data/20232024-undergraduate-catalogue.pdf"

output_csv = "BisonGPT/Data/20232024-formatted-undergraduate-catalogue.csv"
def main():
    with pdfplumber.open(file_p) as pdf:
        structured_text = {}

        current_header = None
        current_subheader = None

        # Iterate over pages starting from page 6 (index 5)
        # The first 5 pages contain the table of contents which is unnecessary
        for page in pdf.pages[5:]:
            lines = page.extract_text_lines()

            for line in lines:
                line_text = line['text']

                # Check for headers (font size > 17)
                if any(char['size'] > 17 for char in line['chars']):
                    current_header = line_text
                    if current_subheader:
                        current_subheader = None
                    structured_text[current_header] = {}
                
                # Check for sub-headers (font size > 10 and <= 18)
                elif any(10 < char['size'] <= 17 for char in line['chars']) or all('Bold' in char['fontname'] for char in line['chars']):
                    current_subheader = line_text
                    if current_header:
                        structured_text[current_header][current_subheader] = []
                
                # Otherwise, it's normal text
                else:
                    if current_header and current_subheader:
                        structured_text[current_header][current_subheader].append(line_text)
                    elif current_header:
                        if "" not in structured_text[current_header]:
                            structured_text[current_header][""] = []
                        structured_text[current_header][""].append(line_text)

    # Write the structured text to a csv file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Header', 'Sub-header', 'Content'])
        for header, subheaders in structured_text.items():
            for subheader, content in subheaders.items():
                writer.writerow([header, subheader, ' '.join(content)])

    print(f"Formatted catalogue saved to {output_csv}")

if __name__ == "__main__":
    main()

