%define name moin
%define version 2.0.0
%define release 0.0.alpha
#Upgrade Path Example:
#     moin-2.0-0.1.beta1
#         Patched
#     moin-2.0-0.2.beta1
#         Move to beta2
#     moin-2.0-0.3.beta2
#         Move to beta3 and simultaneously patch
#     moin-2.0-0.4.beta3
#         Patched again
#     moin-2.0-0.5.beta3
#         Move to rc1
#     moin-2.0-0.6.rc1
#         Move to rc2
#     moin-2.0-0.7.rc2
#         Move to "final"
#     moin-2.0-1
#         Patched
#     moin-2.0-2

Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Summary:        MoinMoin Wiki engine

Group:          Applications/Internet
License:        GPL
URL:            http://moinmo.in/
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArchitectures: noarch
BuildRequires:  python-devel
Requires:       python >= 2.7

%description

A WikiWikiWeb is a collaborative hypertext environment, with an
emphasis on easy access to and modification of information. MoinMoin
is a Python WikiClone that allows you to easily set up your own wiki,
only requiring a Python installation. 

%prep
%setup
echo $RPM_BUILD_ROOT

%build
python setup.py build

%install
python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

#%files -f INSTALLED_FILES   # Wrong: Installed files contains directories also
# This lets rpmbuild complain about Files listed twice.
# A Good explanation is here: "http://www.wideopen.com/archives/rpm-list/2001-February/msg00081.html
%files
%defattr(-,root,root)
/usr
%doc README.txt docs/licenses/COPYING

%changelog
* Sun Jun 21 2010 Thomas Waldmann
- Raised requirement to Python 2.6 (for MoinMoin 2.0.0alpha).
* Sat May 4 2013 Thomas Waldmann
- Raised requirement to Python 2.7 (for MoinMoin 2.0.0alpha).

