from unittest import TestCase, main

from fastpt.v2.text import TextTemplate

class TestBasic(TestCase):

    def setUp(self):
        self.tpl = TextTemplate(source='Hello, ${name}\n')

    def test(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

if __name__ == '__main__':
    main()
