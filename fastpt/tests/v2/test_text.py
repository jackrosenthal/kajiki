from unittest import TestCase, main

from fastpt.v2.text import TextTemplate

class TestBasic(TestCase):

    def test(self):
        tpl = TextTemplate(source='Hello, ${name}\n')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp
        tpl = TextTemplate(source='Hello, $name\n')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp
        tpl = TextTemplate(source='Hello, $obj.name\n')
        class Empty: pass
        Empty.name = 'Rick'
        rsp = tpl(dict(obj=Empty)).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

if __name__ == '__main__':
    main()
