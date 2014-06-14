BUILD_DIR=build_dir
PKG_DIR=packaging
PKG_DIR_DEB=$(PKG_DIR)/deb
PKG_DIR_RPM=$(PKG_DIR)/rpm

all: package-deb-src package-rpm-src
	@echo
	@echo "failover-manager has been fully built"
	@find $(PKG_DIR)

build-dir-prepare:
	mkdir -pv $(BUILD_DIR)
	for DIR in `git ls-files --exclude-standard | xargs dirname`; do mkdir -p $(BUILD_DIR)/$${DIR}; done
	for FILE in `git ls-files --exclude-standard`; do cp -v $${FILE} $(BUILD_DIR)/$${FILE}; done

build-dir-clean:
	rm -rf $(BUILD_DIR)

clean: build-dir-clean

distclean: clean
	rm -rf $(PKG_DIR_RPM)
	rm -rf $(PKG_DIR_DEB)
	rm -rf $(PKG_DIR)

package-deb-src: clean build-dir-prepare
	cd $(BUILD_DIR) && python setup.py --command-packages=stdeb.command sdist_dsc
	mkdir -pv $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/*.tar.gz $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/*.dsc    $(PKG_DIR_DEB)

package-rpm-src: clean build-dir-prepare
	cd $(BUILD_DIR) && python setup.py bdist_rpm --spec-only
	cd $(BUILD_DIR) && python setup.py sdist
	mkdir -pv $(PKG_DIR_RPM)
	cp -vf $(BUILD_DIR)/dist/*.tar.gz $(PKG_DIR_RPM)
	cp -vf $(BUILD_DIR)/dist/*.spec   $(PKG_DIR_RPM)

package-rpm-bin:
	@echo "Not implemented"

package-deb-bin: build-dir-prepare
	cd $(BUILD_DIR) && python setup.py --command-packages=stdeb.command bdist_deb
	mkdir -pv $(PKG_DIR_DEB)
	cp -vf $(BUILD_DIR)/deb_dist/*.deb $(PKG_DIR_DEB)

