from docx.oxml import OxmlElement, ns, parse_xml
from docx.oxml.ns import nsdecls
from docx.oxml.shared import qn
from docx.shared import Cm
from random import randint


def set_row_height(table, heights):
    """

    sets the row height for all table
    :param table: proxy class for a WordprocessingML <w:tbl> element
    :param header_height: (float) specific height for header(first in table) row
    :param height: height (float) height for other rows
    :return:

    """
    for row, height in zip(table.rows, heights):
        row.height = Cm(height)


def create_sdtPr(options, style):
    id = OxmlElement('w:id')
    id.set(qn('w:val'), str(randint(100000000, 999999999)))

    dropDownList = OxmlElement('w:dropDownList')
    for option in options:
        listItem = OxmlElement('w:listItem')
        listItem.set(qn('w:displayText'), option)
        listItem.set(qn('w:value'), option)
        dropDownList.append(listItem)

    sdtPr = OxmlElement('w:sdtPr')
    sdtPr.append(id)
    if style is not None and len(style) > 1:
        sdtPr.append(create_rPr({**style, 'highlight_color': None}))
    sdtPr.append(dropDownList)
    return sdtPr


def create_rPr(style):
    rPr = OxmlElement('w:rPr')
    if 'font_name' in style:
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), style['font_name'])
        rFonts.set(qn('w:hAnsi'), style['font_name'])
        rPr.append(rFonts)

    if 'size' in style:
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), str(2 * style['size']))
        rPr.append(sz)

    if 'highlight_color' in style and style['highlight_color'] is not None:
        highlight = OxmlElement('w:highlight')
        highlight.set(qn('w:val'), style['highlight_color'])
        rPr.append(highlight)
    return rPr


def create_sdtContent(option, style):
    r = OxmlElement('w:r')

    if style is not None:
        r.append(create_rPr(style))

    t = OxmlElement('w:t')
    t.text = option
    r.append(t)
    sdtContent = OxmlElement('w:sdtContent')
    sdtContent.append(r)
    return sdtContent


def create_element(name):
    return OxmlElement(name)


def create_attribute(element, name, value):
    element.set(ns.qn(name), value)


def add_page_number(run, name, bold=False):
    """
    adds the page number (starting with the second) to the footer

    :param run: proxy object wrapping <w:r> element

    """
    run.font.name = name
    run.font.bold = bold

    fld_char1 = create_element('w:fldChar')
    create_attribute(fld_char1, 'w:fldCharType', 'begin')

    instr_text1 = create_element('w:instrText')
    create_attribute(instr_text1, 'xml:space', 'preserve')
    instr_text1.text = " ="

    fld_char2 = create_element('w:fldChar')
    create_attribute(fld_char2, 'w:fldCharType', 'begin')

    instr_text2 = create_element('w:instrText')
    create_attribute(instr_text2, 'xml:space', 'preserve')
    instr_text2.text = "PAGE "

    fld_char3 = create_element('w:fldChar')
    create_attribute(fld_char3, 'w:fldCharType', 'end')

    fld_char4 = create_element('w:fldChar')
    create_attribute(fld_char4, 'w:fldCharType', 'end')

    run._r.append(fld_char1)
    run._r.append(instr_text1)
    run._r.append(fld_char2)
    run._r.append(instr_text2)
    run._r.append(fld_char3)
    run._r.append(fld_char4)


def add_page_count(run, name, bold=False):
    """
    adds the number of pages in a document to the footer

    :param run: proxy object wrapping <w:r> element

    """
    run.font.name = name
    run.font.bold = bold

    fld_char1 = create_element('w:fldChar')
    create_attribute(fld_char1, 'w:fldCharType', 'begin')

    instr_text = create_element('w:instrText')
    create_attribute(instr_text, 'xml:space', 'preserve')
    instr_text.text = "NUMPAGES"

    fld_char2 = create_element('w:fldChar')
    create_attribute(fld_char2, 'w:fldCharType', 'end')
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def add_dropdown_list_in_paragraph(paragraph, options, selected_option, style=None):
    """

    :param cell: class docx.table._Cell, table cell
    :param options: List[str]
    :param selected_option: str from options list
    :param style: dict with keys(font_name, size, highlight_color)
    :return:
    """
    sdt = OxmlElement('w:sdt')
    sdt.append(create_sdtPr(options, style))
    sdt.append(OxmlElement('w:sdtEndPr'))
    sdt.append(create_sdtContent(selected_option, style))
    paragraph._p.append(sdt)


def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    p._p = p._element = None


def set_column_width(table, column, width):
    """

    sets the column width for all table rows
    :param table: proxy class for a WordprocessingML <w:tbl> element
    :param column: (int) number of column
    :param width: width for cell(in Cm, Inches etc)
    :return:

    """
    table.allow_autofit = False
    for row in table.rows:
        row.cells[column].width = width


def set_repeat_table_header(row):
    """
    set repeat table row on every new page

    :param row: _Row object, first table row
    :return: _Row object

    """
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    tblHeader = OxmlElement('w:tblHeader')
    tblHeader.set(ns.qn('w:val'), "true")
    trPr.append(tblHeader)
    return row


def create_list(paragraph, list_type='1'):
    """

    modifies a paragraph into a list item
    :param paragraph: proxy object wrapping <w:p> element
    :param list_type: (int) number of type list
    :return:

    """
    p = paragraph._p
    p_pr = p.get_or_add_pPr()
    num_pr = OxmlElement('w:numPr')
    num_id = OxmlElement('w:numId')
    num_id.set(ns.qn('w:val'), list_type)
    num_pr.append(num_id)
    p_pr.append(num_pr)


def indent_table(table, indent):
    """
    sets the left indent for the table

    :param table: proxy class for a WordprocessingML <w:tbl> element
    :param indent: (float) left indent for table in centimeters(Cm)
    :return:

    """
    # noinspection PyProtectedMember
    tbl_pr = table._element.xpath('w:tblPr')
    if tbl_pr:
        e = OxmlElement('w:tblInd')
        e.set(ns.qn('w:w'), str(indent))
        e.set(ns.qn('w:type'), 'dxa')
        tbl_pr[0].append(e)


def set_sell_color(cell, color):
    # set a cell background (shading) color to RGB.
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color))
    cell._tc.get_or_add_tcPr().append(shading_elm)
