from pathlib import Path
import unittest


class WebmasterVerificationTest(unittest.TestCase):
    def test_home_shell_exposes_new_fbrk_webmaster_verification_tags(self) -> None:
        html = Path("index.html").read_text(encoding="utf-8")

        self.assertIn(
            'meta name="google-site-verification" content="Z9rVFdqvBmGx64dSre-kpREQO-sm2aa8F_IsBGHlrN8"',
            html,
        )
        self.assertIn(
            'meta name="yandex-verification" content="979d9e3c1c452d5b"',
            html,
        )


if __name__ == "__main__":
    unittest.main()
