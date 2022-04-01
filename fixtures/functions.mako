## Helper template functions downloading/extracting files
<%def name="setup_env()">
if ! test -f "/usr/local/bin/pacapt"; then
    wget -O /usr/local/bin/pacapt https://github.com/icy/pacapt/raw/ng/pacapt
    chmod 755 /usr/local/bin/pacapt
    ln -sv /usr/local/bin/pacapt /usr/local/bin/pacman || true
fi
</%def>

<%def name="install_pkgs(pkgs)">
% for pkg in pkgs:
pacapt install --noconfirm ${pkg}
% endfor
</%def>

<%def name="download(url, src_file)">
wget -O ${src_file} ${url}
</%def>

<%def name="extract(src, dst=None)">
% if dst:
mkdir -p ${dst}
tar -xf ${src} -C ${dst}
% else:
tar -xf ${src}
% endif
</%def>