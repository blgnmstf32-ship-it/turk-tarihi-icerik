import unittest

from PIL import Image, ImageDraw

from scripts.commons_media import _allowed_license, _fingerprint, _metadata, _portrait


class CommonsLicenseTests(unittest.TestCase):
    def test_wide_framing_preserves_both_edges_and_resize_is_near_duplicate(self):
        original = Image.new('RGB', (1200, 600), 'navy')
        draw = ImageDraw.Draw(original)
        draw.rectangle((0, 0, 200, 599), fill='red')
        draw.rectangle((999, 0, 1199, 599), fill='yellow')
        proposed, framing = _portrait(original)
        self.assertEqual((proposed.size, framing), ((1080, 1920), 'full_image_on_matte'))
        self.assertEqual(proposed.getpixel((50, 800)), (255, 0, 0))
        self.assertEqual(proposed.getpixel((1030, 800)), (255, 255, 0))
        scaled = original.resize((800, 400), Image.Resampling.LANCZOS)
        self.assertLessEqual((_fingerprint(original) ^ _fingerprint(scaled)).bit_count(), 4)

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
