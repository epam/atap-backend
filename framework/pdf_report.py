from fpdf import FPDF


# os.environ["FPDF_FONTPATH"] = os.getcwd()+"/font"


def draw_textbox(pdf: FPDF, bg_color, text, line_height=10, additional_height=0):

    prev_x = pdf.get_x()
    prev_y = pdf.get_y()

    margin = 2

    pdf.set_fill_color(*bg_color)

    line_width = pdf.w - pdf.l_margin - pdf.r_margin
    line_count = 0
    for manual_line in text.split('\n'):
        line_count += 1 + int((pdf.get_string_width(manual_line)+margin) // line_width)

    if prev_y + line_count*line_height + additional_height + margin > pdf.h - pdf.b_margin:
        pdf.add_page()
        prev_y = pdf.t_margin
        pdf.set_y(pdf.t_margin)

    pdf.rect(prev_x, prev_y, line_width, line_height*line_count + additional_height, style="FD")
    pdf.get_string_width(text)

    pdf.set_xy(prev_x, prev_y)
    pdf.write(line_height, text)

    pdf.set_xy(prev_x, prev_y + line_height*line_count + additional_height)


def pdf_from_report(report, filename):
    print("Rendering pdf...")
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('FreeSerif', '', '/freefont-20100919/FreeSerif.ttf', uni=True)
    pdf.add_font('FreeSerif', 'B', '/freefont-20100919/FreeSerifBold.ttf', uni=True)
    issue_id = 0
    failed_test_count = 0
    pdf.set_font("FreeSerif", "BU", 20)
    pdf.write(10, f"Ran {len(report)} tests in total:")
    pdf.ln()
    pdf.set_font("FreeSerif", "", 15)
    for test_id, test in enumerate([test for test in report if test.visible]):
        pdf.write(8, f"{test_id+1}. {test.human_name}")
        pdf.ln()
    for test in report:
        if test.status in ["PASS", "NOELEMENTS"]:
            continue
        failed_test_count += 1
        issue_id += 1
        pdf.set_font("FreeSerif", "BU", 20)
        pdf.write(10, f"Issue {issue_id}: {test.human_name}")
        pdf.ln()
        pdf.set_font("FreeSerif", "B", 16)
        if test.message is not None:
            pdf.write(10, f"Problem: ")
            pdf.set_font("FreeSerif", "", 16)
            pdf.write(10, test.message)
        else:
            pdf.write(10, "No message from test")
        pdf.ln()
        if len(test.problematic_elements) > 0:
            for element_id, element in enumerate(test.problematic_elements):
                pdf.set_font("FreeSerif", "", 14)
                source = element['element'].source if 'element' in element else element['source']
                if len(source) > 150:
                    source = source[:150] + " ... "
                additional_height = 0
                if "screenshot" in element:
                    screenshot_margin = 2
                    screenshot_width = (pdf.w - pdf.l_margin - pdf.r_margin)/2
                    screenshot_height = element['screenshot_height']*screenshot_width/element['screenshot_width']
                    additional_height = screenshot_height + screenshot_margin*2
                draw_textbox(pdf, (255, 200, 200), f"Problematic element {element_id + 1}:\n{element['problem']}", 7, additional_height)
                if "screenshot" in element:
                    pdf.image(
                        element["screenshot"],
                        pdf.get_x() + screenshot_margin,
                        pdf.get_y() - screenshot_height - screenshot_margin,
                        screenshot_width,
                        screenshot_height
                    )

                pdf.set_font("FreeSerif", "", 12)
                draw_textbox(pdf, (200, 200, 255), f"Snippet: {source}", 7)
                pdf.ln()
        pdf.ln()
    if failed_test_count == 0:
        pdf.set_font("FreeSerif", "BU", 20)
        pdf.write(10, f"All tests have passed")
        pdf.ln()

    print("Saving PDF...")
    pdf.output(filename, "F")
    print("Done!")
