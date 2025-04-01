import unittest


class Test_Sample01(unittest.TestCase):

    def test_sum(self):

        self.assertTrue(21 == sum(10, 11))


if __name__ == "__main__":
    unittest.main()
