"""Verify actual OOXML reports, their header structure and access boundaries."""
from datetime import datetime, timezone
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET

# Reuse only HTTP harness; it starts disposable SQLite and never touches user data.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_workflow import WorkflowAcceptance

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def workbook(data):
    with ZipFile(BytesIO(data)) as archive:
        assert archive.testzip() is None
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(i.itertext()) for i in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        cells = {}
        for cell in sheet.findall('.//s:sheetData/s:row/s:c', NS):
            if cell.get('t') == 's':
                text = shared[int(cell.find('s:v', NS).text)]
            elif cell.get('t') == 'inlineStr':
                text = ''.join(t.text or '' for t in cell.findall('.//s:t', NS))
            else:
                value = cell.find('s:v', NS)
                text = value.text if value is not None else ''
            cells[cell.get('r')] = text
        merges = {m.get('ref') for m in sheet.findall('.//s:mergeCell', NS)}
        return {'cells': cells, 'merges': merges, 'sheet': sheet,
                'parts': archive.namelist(), 'workbook': ET.fromstring(archive.read('xl/workbook.xml'))}


def fixture():
    def request(id, status, **extra):
        row = {'id': id, 'number': f'NAV-{id:04}', 'queue_number': f'A-{id:03}',
               'created_at': '2026-11-16T21:30:00+00:00', 'content': 'Transkript olish',
               'channel': 'kiosk', 'status': status, 'student_id': '100000000001',
               'student': {'full_name': 'Sinov Talaba', 'programme': '00123456', 'faculty':'Sinov fakulteti', 'course': 3,
                           'education_form': 'Kunduzgi'}, 'manager_id': 3, 'manager_name': 'Sinov Menejer',
               'assignee_id': None, 'assignee_name': None, 'deadline': None,
               'answer': '', 'result': '', 'unresolved_reason': '', 'closed_at': None}
        row.update(extra)
        return row
    return {'summary': {'total': 3, 'closed': 1, 'in_progress': 2, 'overdue': 0, 'on_time': 1},
            'requests': [request(1, 'closed', result='Talabaga transkript berildi', answer='Tayyor', closed_at='2026-11-17T01:00:00+00:00'),
                         request(2, 'in_progress', channel='phone', assignee_id=4, assignee_name='Sinov Ijrochi', deadline='2026-11-18T21:00:00+00:00'),
                         request(3, 'returned', channel='lms', unresolved_reason='Ilova yetishmaydi')],
            'departments': [], 'daily': []}


class ExcelStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('navbot_excel', ROOT / 'navbot' / 'excel.py')
        cls.excel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.excel)

    def test_real_ooxml_merged_headers_and_data_columns(self):
        report = workbook(self.excel.build(fixture()))
        for part in ['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels',
                     'xl/worksheets/sheet1.xml', 'xl/styles.xml']:
            self.assertIn(part, report['parts'])
        expected = {'A1:M1', 'A4:A5', 'B4:B5', 'C4:C5', 'D4:D5', 'E4:E5', 'F4:F5', 'G4:G5', 'H4:H5', 'I4:I5', 'J4:L4', 'M4:M5'}
        self.assertTrue(expected.issubset(report['merges']), report['merges'])
        cells = report['cells']
        self.assertEqual(cells['A4'], 'Sana')
        self.assertEqual(cells['B4'], 'T/r')
        self.assertIn('F.I.', cells['C4'])
        self.assertEqual(cells['F4'], 'Kurs')
        self.assertEqual(cells['J4'], 'Körilgan çora')
        self.assertEqual(cells['J5'], 'Hal etildi')
        self.assertIn('Yönaltirildi', cells['K5'])
        self.assertIn('Hal etilmadi', cells['L5'])
        self.assertIn('Qabul qilgan xodim', cells['I4'])
        self.assertIn('Murojaat qiliş usuli', cells['M4'])
        self.assertEqual(cells['B6'], '1')
        self.assertEqual(cells['C6'], 'Sinov Talaba')
        self.assertEqual(cells['D4'], 'Fakultet')
        self.assertEqual(cells['E4'], 'Mutaxassislik şifri')
        self.assertEqual(cells['D6'], 'Sinov fakulteti')
        self.assertEqual(cells['E6'], '00123456')
        self.assertEqual(cells['F6'], '3')
        self.assertEqual(cells['G6'], 'Kunduzgi')
        self.assertEqual(cells['H6'], 'Transkript olish')
        self.assertEqual(cells['M6'], 'NavBoT')
        self.assertIn('Talabaga transkript berildi', cells['J6'])
        self.assertEqual(cells['M7'].lower(), 'telefon')
        self.assertIn('2026', cells['K7'])
        self.assertEqual(cells['M8'], 'LMS')
        self.assertIn('Ilova yetishmaydi', cells['L8'])
        self.assertEqual(cells['I6'], 'Sinov Menejer')
        self.assertIsNotNone(report['sheet'].find('s:cols', NS), 'Readable column widths required')

    def test_referral_only_for_another_staff_member(self):
        report = fixture()
        row = report['requests'][0]
        row.update(assignee_id=3, assignee_name='Sinov Menejer', deadline='2026-11-18T21:00:00+00:00')
        for status in ('in_progress', 'closed'):
            row['status'] = status
            cells = workbook(self.excel.build(report))['cells']
            self.assertEqual(cells['K6'], '')
            self.assertEqual(cells['I6'], 'Sinov Menejer')
        row.update(assignee_id=4, assignee_name='Boshqa Xodim')
        for status in ('in_progress', 'closed'):
            row['status'] = status
            cells = workbook(self.excel.build(report))['cells']
            self.assertEqual(cells['K6'], 'Boshqa Xodim\n19.11.2026 02:00')
            self.assertEqual(cells['I6'], 'Sinov Menejer')
        row['deadline'] = None
        self.assertEqual(workbook(self.excel.build(report))['cells']['K6'], 'Boshqa Xodim')

    def test_dates_are_tashkent_calendar_not_utc(self):
        cells = workbook(self.excel.build(fixture()))['cells']
        # 16 Nov21:30UTC is 17 Nov02:30 in Tashkent.
        self.assertRegex(cells['A6'], r'(17[./-]11[./-]2026|2026[./-]11[./-]17)')
        # Deadline18 Nov21UTC crosses into 19 Nov02:00Tashkent.
        self.assertRegex(cells['K7'], r'(19[./-]11[./-]2026|2026[./-]11[./-]19)')

    def test_formula_looking_student_text_is_literal_not_formula(self):
        report = fixture()
        row = report['requests'][0]
        row['student']['full_name'] = '=HYPERLINK("https://evil.example","click")'
        row['content'] = '+SUM(1,2) <script> & тест'
        row['result'] = '@DangerousFormula'
        parsed = workbook(self.excel.build(report))
        self.assertEqual(parsed['cells']['C6'], row['student']['full_name'])
        self.assertEqual(parsed['cells']['H6'], row['content'])
        self.assertEqual(parsed['sheet'].findall('.//s:f', NS), [], 'User text must never become Excel formulas')
        cell = parsed['sheet'].find('.//s:c[@r="C6"]', NS)
        self.assertIn(cell.get('t'), ('inlineStr', 's'))

    def test_empty_report_still_has_header_and_no_phantom_rows(self):
        report = fixture()
        report['requests'] = []
        parsed = workbook(self.excel.build(report))
        self.assertIn('J4:L4', parsed['merges'])
        self.assertNotIn('A6', parsed['cells'])
        self.assertNotIn('C6', parsed['cells'])

    def test_all_three_header_languages_and_invalid_language(self):
        expected = {'uz': 'Sana', 'ru': 'Дата', 'en': 'Date'}
        for lang, first in expected.items():
            with self.subTest(lang=lang):
                parsed = workbook(self.excel.build(fixture(), lang=lang))
                self.assertEqual(parsed['cells']['A4'], first)
                self.assertEqual(parsed['cells']['D4'],{'uz':'Fakultet','ru':'Факультет','en':'Faculty'}[lang])
                self.assertEqual(parsed['cells']['E4'],{'uz':'Mutaxassislik şifri','ru':'Код специальности','en':'Specialty code'}[lang])
                self.assertEqual(parsed['cells']['D6'],'Sinov fakulteti')
                self.assertEqual(parsed['cells']['E6'],'00123456')
                self.assertEqual(parsed['cells']['A1'], self.excel.LABELS[lang]['title'])
                self.assertEqual(parsed['cells']['A2'], self.excel.LABELS[lang]['subtitle'])
                self.assertIn(self.excel.LABELS[lang]['period'], parsed['cells']['A3'])
                self.assertIn('A3:M3', parsed['merges'])
                self.assertEqual(parsed['sheet'].find('s:sheetViews/s:sheetView', NS).get('showGridLines'), '1')
                self.assertEqual(parsed['cells']['I4'], self.excel.LABELS[lang]['headers'][10])
                self.assertEqual(parsed['cells']['M4'], self.excel.LABELS[lang]['headers'][8])
                self.assertEqual(parsed['cells']['I6'], 'Sinov Menejer')
                self.assertEqual(parsed['cells']['M6'], 'NavBoT')
                self.assertIn('J4:L4', parsed['merges'])
        # A supplied unsupported language must be rejected or use a documented safe default.
        try:
            data = self.excel.build(fixture(), lang='bad-language')
        except (ValueError, KeyError):
            return
        self.assertEqual(workbook(data)['cells']['A4'], 'Sana')


class ExcelEndpoint(WorkflowAcceptance):
    # Avoid inheriting the base acceptance methods into this focused suite.
    def test_xlsx_requires_report_role_and_matches_scoped_filtered_registry(self):
        _, request = self.assigned_request()
        self.assertEqual(self.public.request('/api/report.xlsx')[0], 401)
        self.assertEqual(self.client('manager').request('/api/report.xlsx')[0], 403)
        self.assertEqual(self.client('executor').request('/api/report.xlsx')[0], 403)
        # The HTTP harness decodes text responses, so fetch binary with its authenticated opener.
        for username in ('admin', 'director', 'head'):
            with self.subTest(username=username):
                client = self.client(username)
                response = client.opener.open(self.base + '/api/report.xlsx', timeout=8)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.assertIn('.xlsx', response.headers.get('Content-Disposition', ''))
                parsed = workbook(response.read())
                self.assertEqual(parsed['cells']['C6'], 'Sinov Talaba Bir')
                self.assertEqual(parsed['cells']['I6'], 'Sinov Menejer 1')
                response.close()
        response = self.client('director').opener.open(self.base + '/api/report.xlsx?channel=phone', timeout=8)
        parsed = workbook(response.read())
        self.assertNotIn('C6', parsed['cells'])
        response.close()


# Expose only the XLSX endpoint test instead of rerunning inherited acceptance here.
for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in ExcelEndpoint.__dict__:
        setattr(ExcelEndpoint, _name, None)
del WorkflowAcceptance

if __name__ == '__main__':
    unittest.main(verbosity=2)
