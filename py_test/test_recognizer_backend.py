"""模板识别后端选择测试"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '.')

import vision.recognizer as recognizer


class TestTemplateRecognizerBackend(unittest.TestCase):
    def test_explicit_cpu_mode_disables_gpu_even_when_cuda_available(self):
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: True,
                get_device_name=lambda index: "Fake GPU",
            ),
            device=lambda name: f"device:{name}",
        )

        templates_dir = Path('templates')
        with patch.object(recognizer, 'TORCH_AVAILABLE', True), patch.object(recognizer, 'torch', fake_torch):
            template_recognizer = recognizer.TemplateRecognizer(str(templates_dir), use_gpu=False)

        self.assertFalse(template_recognizer.use_gpu)
        self.assertIsNone(template_recognizer.device)


if __name__ == '__main__':
    unittest.main()
