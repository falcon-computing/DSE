


#echo "ALTERA_QUARTUS_HOME     = $ALTERA_QUARTUS_HOME"
#echo "ALTERAOCLSDKROOT        = $ALTERAOCLSDKROOT"
#echo "AOCL_BOARD_PACKAGE_ROOT = $AOCL_BOARD_PACKAGE_ROOT"

#setenv ALTERA_VERSION_PATH /curr/software/Altera/15.1/
setenv ALTERA_VERSION_PATH $ALTERA_QUARTUS_HOME
setenv QUARTUS_ROOTDIR $ALTERA_VERSION_PATH/quartus
#setenv LD_LIBRARY_PATH $QUARTUS_ROOTDIR/linux64:${LD_LIBRARY_PATH}
#setenv PATH $ALTERA_VERSION_PATH/quartus/bin/:$PATH

#setenv ALTERAOCLSDKROOT $ALTERA_VERSION_PATH/hld
setenv PATH $QUARTUS_ROOTDIR/bin:$PATH
setenv PATH $QUARTUS_ROOTDIR/sopc_builder/bin:$PATH
setenv PATH $QUARTUS_ROOTDIR/../qsys/bin/:$PATH
setenv PATH $ALTERAOCLSDKROOT/bin/:$PATH
setenv PATH $ALTERAOCLSDKROOT/linux64/bin/:$PATH
setenv LD_LIBRARY_PATH $ALTERAOCLSDKROOT/linux64/lib:${LD_LIBRARY_PATH}
setenv LD_LIBRARY_PATH $ALTERAOCLSDKROOT/host/lin64/lib:${LD_LIBRARY_PATH}
setenv LD_LIBRARY_PATH $ALTERAOCLSDKROOT/host/linux64/lib:${LD_LIBRARY_PATH}
#setenv AOCL_BOARD_PACKAGE_ROOT $ALTERA_VERSION_PATH/hld/board/terasic/de5net
setenv LD_LIBRARY_PATH $AOCL_BOARD_PACKAGE_ROOT/linux64/lib:${LD_LIBRARY_PATH}
setenv ACL_PROFILE_TIMER 1
