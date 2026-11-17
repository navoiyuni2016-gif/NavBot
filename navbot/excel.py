"""Excel OOXML report matching the registrar's two-level paper table."""
from datetime import datetime, timedelta, timezone
import io
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

LABELS = {
 'uz': {
  'title': 'Alişer Navoiy nomidagi Toşkent davlat özbek tili va adabiyoti universiteti',
  'subtitle': 'REGISTRATOR OFISI · MUROJAATLAR STATISTIKASI',
  'period': 'Davr', 'all': 'Barça sanalar',
  'headers': ['Sana', 'T/r', 'Murojaatçining F.I.Ş.', 'Ta’lim yönalişi (mutaxassisligi)', 'Kurs', 'Ta’lim şekli', 'Murojaat mazmuni', 'Murojaat qiliş usuli (NavBoT, telefon, LMS)', 'Körilgan çora', 'Mas’ul menejer F.I.Ş.'],
  'sub': ['Hal etildi', 'Yönaltirildi (muddat)', 'Hal etilmadi (sabab)'],
  'phone': 'Telefon', 'unknown': 'Noma’lum', 'total': 'Jami murojaatlar',
 },
 'ru': {
  'title': 'Ташкентский государственный университет узбекского языка и литературы имени Алишера Навои',
  'subtitle': 'ОФИС РЕГИСТРАТОРА · СТАТИСТИКА ОБРАЩЕНИЙ',
  'period': 'Период', 'all': 'Все даты',
  'headers': ['Дата', '№ п/п', 'Ф.И.О. заявителя', 'Направление подготовки (специальность)', 'Курс', 'Форма обучения', 'Содержание обращения', 'Способ обращения (NavBoT, телефон, LMS)', 'Принятые меры', 'Ф.И.О. ответственного менеджера'],
  'sub': ['Решено', 'Направлено (срок)', 'Не решено (причина)'],
  'phone': 'Телефон', 'unknown': 'Неизвестно', 'total': 'Всего обращений',
 },
 'en': {
  'title': 'Alisher Navo’i Tashkent State University of Uzbek Language and Literature',
  'subtitle': 'REGISTRAR’S OFFICE · REQUEST STATISTICS',
  'period': 'Period', 'all': 'All dates',
  'headers': ['Date', 'No.', 'Applicant’s full name', 'Programme (specialisation)', 'Year', 'Mode of study', 'Request content', 'Channel (NavBoT, telephone, LMS)', 'Action taken', 'Responsible manager’s full name'],
  'sub': ['Resolved', 'Referred (deadline)', 'Unresolved (reason)'],
  'phone': 'Telephone', 'unknown': 'Unknown', 'total': 'Total requests',
 },
}
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def clean(value):
    # XML 1.0 rejects control characters; spreadsheet cells max 32767 characters.
    return ''.join(c for c in str(value) if c in '\t\n\r' or 32 <= ord(c) <= 0xd7ff or 0xe000 <= ord(c) <= 0xfffd or 0x10000 <= ord(c) <= 0x10ffff)[:32767]


def display_date(value):
    if not value:
        return ''
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone(timedelta(hours=5))).strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return str(value)


def education_form(value, lang):
    forms = {'Kunduzgi': ['Kunduzgi','Очная','Full-time'], 'Sirtqi': ['Sirtqi','Заочная','Part-time'],
             'Kechki': ['Keçki','Вечерняя','Evening'], 'Keçki': ['Keçki','Вечерняя','Evening'],
             'Masofaviy': ['Masofaviy','Дистанционная','Distance learning']}
    return forms[value][{'uz':0,'ru':1,'en':2}.get(lang,0)] if value in forms else value


def cell(ref, value='', style=0):
    if value is None:
        value = ''
    if type(value) in (int, float):
        return f'<c r="{ref}" s="{style}" t="n"><v>{value}</v></c>'
    # Explicit inline strings ensure = + - @ content never becomes an Excel formula.
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(clean(value))}</t></is></c>'


def build(report, lang='uz', period=None):
    labels = LABELS.get(lang, LABELS['uz'])
    rows = []
    def row(number, values, style=0, height=None):
        attrs = f' ht="{height}" customHeight="1"' if height else ''
        rows.append(f'<row r="{number}"{attrs}>' + ''.join(cell(chr(65 + i) + str(number), value, style) for i, value in enumerate(values)) + '</row>')
    row(1, [labels['title']], 1, 48)
    row(2, [labels['subtitle']], 6, 28)
    row(3, [labels['period'] + ': ' + (period or labels['all'])], 2, 26)
    top = labels['headers']
    row(4, top[:7] + [top[9], top[8], '', '', top[7]], 3, 42)
    row(5, [''] * 8 + labels['sub'] + [''], 3, 35)
    for index, request in enumerate(report.get('requests', []), 1):
        student = request.get('student') or {}
        referred = ''
        if request.get('assignee_id') and request.get('deadline'):
            referred = (request.get('assignee_name') or '') + '\n' + display_date(request['deadline'])
        closed = request.get('status') == 'closed'
        values = [display_date(request.get('created_at')), index, student.get('full_name', ''), student.get('programme', ''),
                  student.get('course', ''), education_form(student.get('education_form', ''),lang), request.get('content', ''),
                  request.get('manager_name') or '',
                  (request.get('result') or request.get('answer') or '') if closed else '', referred,
                  request.get('unresolved_reason') or '',
                  {'kiosk': 'NavBoT', 'phone': labels['phone'], 'lms': 'LMS'}.get(request.get('channel'), labels['unknown'])]
        row(index + 5, values, 4 if index % 2 else 5, 60)
    last = 5 + len(report.get('requests', []))
    row(last + 2, [labels['total'], len(report.get('requests', []))], 2, 25)
    merges = ['A1:L1', 'A2:L2', 'A3:L3', f'C{last+2}:L{last+2}'] + [f'{col}4:{col}5' for col in 'ABCDEFGH'] + ['I4:K4', 'L4:L5']
    widths = [19, 7, 30, 34, 8, 20, 44, 30, 34, 36, 35, 23]
    cols = ''.join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i, width in enumerate(widths, 1))
    sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{NS}"><sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><dimension ref="A1:L{last+2}"/>
<sheetViews><sheetView workbookViewId="0" showGridLines="0"><pane ySplit="5" topLeftCell="A6" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<sheetFormatPr defaultRowHeight="20"/><cols>{cols}</cols><sheetData>{''.join(rows)}</sheetData>
<mergeCells count="{len(merges)}">{''.join('<mergeCell ref="'+m+'"/>' for m in merges)}</mergeCells>
<printOptions horizontalCentered="1"/><pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.2"/>
<pageSetup paperSize="8" orientation="landscape" fitToWidth="1" fitToHeight="0"/>
</worksheet>'''
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{NS}">
<fonts count="4"><font><sz val="11"/><color rgb="FF142E45"/><name val="Calibri"/></font><font><b/><sz val="20"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FF006C64"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="6"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE2F1EC"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF142E45"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF007E73"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF1F8F7"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"><color rgb="FF57736C"/></left><right style="thin"><color rgb="FF57736C"/></right><top style="thin"><color rgb="FF57736C"/></top><bottom style="thin"><color rgb="FF57736C"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="7"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="4" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="3" fillId="4" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    files = {
      '[Content_Types].xml': '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
      '_rels/.rels': '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
      'xl/workbook.xml': f'''<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets><sheet name="{ {'uz':'Hisobot','ru':'Отчёт','en':'Report'}.get(lang,'Hisobot')}" sheetId="1" r:id="rId1"/></sheets><definedNames><definedName name="_xlnm.Print_Titles" localSheetId="0">'{ {'uz':'Hisobot','ru':'Отчёт','en':'Report'}.get(lang,'Hisobot')}'!$4:$5</definedName></definedNames></workbook>''',
      'xl/_rels/workbook.xml.rels': '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
      'xl/worksheets/sheet1.xml': sheet, 'xl/styles.xml': styles,
    }
    out = io.BytesIO()
    with ZipFile(out, 'w', ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body.encode('utf-8'))
    return out.getvalue()
