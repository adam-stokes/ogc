## Helper template functions downloading/extracting files
<%def name="setup_env()">
if ! test -f "/usr/local/bin/pacapt"; then
    sudo wget -O /usr/local/bin/pacapt https://github.com/icy/pacapt/raw/ng/pacapt
    sudo chmod 755 /usr/local/bin/pacapt
    sudo ln -sv /usr/local/bin/pacapt /usr/local/bin/pacman || true
fi
</%def>

<%def name="install_pkgs(pkgs)">
% for pkg in pkgs:
sudo pacapt install --noconfirm ${pkg}
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

<%def name="run(exe, *args, **kwargs)">
<% 
import sh
cmd = sh.Command(exe)
cmd = str(cmd.bake(*args, **kwargs))
%>
${cmd}
</%def>