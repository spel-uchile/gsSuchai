all:
	cd forms; sh build_forms.sh --force
	git describe --abbrev=0 > config/version.txt
	@/usr/bin/env python2 setup.py sdist
	
python3:
	cd forms; sh build_forms.sh --force
	git describe --abbrev=0 > config/version.txt
	@/usr/bin/env python3 setup.py sdist

.PHONY: all
