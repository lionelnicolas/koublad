BUILD_DIR:=build_dir
PACKAGE:=koublad
VERSION:=0.1.1-$(shell date +%s)

PKG_DIR=packaging
PKG_DIR_DEB=$(PKG_DIR)/deb
PKG_DIR_RPM=$(PKG_DIR)/rpm

all: distclean package-deb-bin package-rpm-bin
	@echo
	@echo "$(PACKAGE) has been fully built"
	@find $(PKG_DIR)

all-src: distclean package-deb-src package-rpm-src
	@echo
	@echo "$(PACKAGE) has been fully built"
	@find $(PKG_DIR)

build-dir-prepare: clean
	mkdir -pv $(BUILD_DIR)
	for FILE in `git ls-files --exclude-standard`; do mkdir -p $(BUILD_DIR)/`dirname $${FILE}`; cp -v $${FILE} $(BUILD_DIR)/$${FILE}; done
	mv $(BUILD_DIR)/koublad.init $(BUILD_DIR)/koublad
	/bin/echo -ne "PACKAGE=\"$(PACKAGE)\"\nVERSION=\"$(VERSION)\"\n" >$(BUILD_DIR)/_vars.py
	/bin/echo -ne "include *.conf\ninclude *.py\nrecursive-include plugins *.py\n" >$(BUILD_DIR)/MANIFEST.in

build-dir-clean:
	rm -rf $(BUILD_DIR)

clean: build-dir-clean

distclean: clean
	rm -rf $(PKG_DIR_RPM)
	rm -rf $(PKG_DIR_DEB)
	rm -rf $(PKG_DIR)

package-deb-src: build-dir-prepare
	cd $(BUILD_DIR) && python setup.py --command-packages=stdeb.command sdist_dsc
	mkdir -pv $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/*.tar.gz $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/*.dsc    $(PKG_DIR_DEB)

package-deb-bin: package-deb-src
	cd $(BUILD_DIR) && python setup.py --command-packages=stdeb.command bdist_deb
	mkdir -pv $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/$(PACKAGE)*.deb $(PKG_DIR_DEB)

package-rpm-src: build-dir-prepare
	cd $(BUILD_DIR) && python setup.py bdist_rpm --spec-only
	cd $(BUILD_DIR) && python setup.py sdist
	sed -ri 's#(python setup.py install .*)#\1\nsed -ri "s@^(.*\.py)@\\1*@" INSTALLED_FILES#' $(BUILD_DIR)/dist/$(PACKAGE).spec
	/bin/echo -e "\n%config(noreplace)\n/etc/koublad.conf" >>$(BUILD_DIR)/dist/$(PACKAGE).spec
	mkdir -pv $(PKG_DIR_RPM)
	cp -vf $(BUILD_DIR)/dist/$(PACKAGE)*.tar.gz $(PKG_DIR_RPM)
	cp -vf $(BUILD_DIR)/dist/$(PACKAGE).spec    $(PKG_DIR_RPM)

package-rpm-bin: package-rpm-src
	mkdir -p $(BUILD_DIR)/dist/SOURCES
	cp $(BUILD_DIR)/dist/$(PACKAGE)*.tar.gz $(BUILD_DIR)/dist/SOURCES
	cd $(BUILD_DIR)/dist && rpmbuild --define "_topdir `pwd`" -ba $(PACKAGE).spec
	find $(BUILD_DIR)/dist -name '*.rpm' -exec cp -v {} $(PKG_DIR_RPM) \;

