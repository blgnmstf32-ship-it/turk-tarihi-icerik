import unittest

from scripts.commons_media import _allowed_license, _metadata


class CommonsLicenseTests(unittest.TestCase):
    def test_accepts_explicit_free_licenses(self):
        for name in ('Public domain','CC0 1.0','CC BY 4.0','CC BY-SA 3.0'):
            with self.subTest(name=name):self.assertTrue(_allowed_license(name))

    def test_rejects_noncommercial_or_unknown_license(self):
        for name in ('CC BY-NC 4.0','All rights reserved',''):
            with self.subTest(name=name):self.assertFalse(_allowed_license(name))

    def test_metadata_keeps_attribution_and_source_page(self):
        page={'title':'File:Old Stone Relief.jpg','imageinfo':[{'mediatype':'BITMAP','mime':'image/jpeg','url':'https://upload.wikimedia.org/example.jpg',
          'thumburl':'https://upload.wikimedia.org/thumb.jpg','extmetadata':{
            'ObjectName':{'value':'Stone relief'},'Artist':{'value':'<a>Archive Author</a>'},
            'LicenseShortName':{'value':'CC BY 4.0'},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by/4.0/'}}}]}
        item=_metadata(page)
        self.assertEqual(item['artist'],'Archive Author')
        self.assertEqual(item['license'],'CC BY 4.0')
        self.assertIn('File:Old_Stone_Relief.jpg',item['description_url'])


if __name__=='__main__':unittest.main()
