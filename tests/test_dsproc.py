from autodse import dsproc

def test_check_option_syntax():
    # Basic
    ds_opt0 = "[32,64,128,256,512]"
    ret0 = dsproc.check_option_syntax(ds_opt0)
    assert ret0[0] == True, 'expect success'
    assert not ret0[1], 'expect no dependency'

    # Dependency
    ds_opt1 = ("[x for x in ['','reduction = dist'] "
              "if x=='' or (CGPIP1!='flatten' and CGPIP2!='flatten')]")
    ret1 = dsproc.check_option_syntax(ds_opt1)
    assert ret1[0] == True, 'expect success'
    assert len(ret1[1]) == 2 and sorted(ret1[1]) == ['CGPIP1', 'CGPIP2'], 'expect 2 dependencies'

    # Syntax error
    ds_opt2 = "[x, y for x in [1,2,4,8,16]]"
    ret2 = dsproc.check_option_syntax(ds_opt2)
    assert ret2[0] == False, 'expect failure'

    # The use of legel builtin functions
    ds_opt3 = "[sqrt(x) for x in range(20)]"
    ret3 = dsproc.check_option_syntax(ds_opt3)
    assert ret3[0] == True, 'expect success'
    assert len(ret3[1]) == 0, 'expect no dependency'

    # The use of legal type casting
    ds_opt4 = "[int(x) for x in [1,2,3,4,5,6]]"
    ret4 = dsproc.check_option_syntax(ds_opt4)
    assert ret4[0] == True, 'expect success'
    assert len(ret4[1]) == 0, 'expect no dependency'

if __name__ == "__main__":
    test_check_option_syntax()
