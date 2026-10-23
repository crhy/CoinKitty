import unittest

from coinkitty_wallet.pages import PAGES, BOTTOM_BAR, page_title


class PagesTest(unittest.TestCase):
    def test_ids_unique(self):
        ids = [page_id for page_id, _title, _icon in PAGES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_bottom_bar_ids_in_pages(self):
        ids = {page_id for page_id, _title, _icon in PAGES}
        for page_id in BOTTOM_BAR:
            self.assertIn(page_id, ids)

    def test_page_title_known(self):
        self.assertEqual(page_title("home"), "Home")
        self.assertEqual(page_title("launch-window"), "Launch Window")

    def test_page_title_unknown_raises(self):
        with self.assertRaises(KeyError):
            page_title("does-not-exist")


if __name__ == "__main__":
    unittest.main()
