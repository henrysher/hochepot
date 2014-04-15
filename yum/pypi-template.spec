
{# prints a single dependency for a specific python version #}
{%- macro one_dep(dep) %}
{{ dep[0] }}:{{ ' ' * (15 - dep[0]|length) }}{{ dep[1]|name_for_python_version(27) }}{% if dep[2] is defined %} {{ dep[2] }} {{ dep[3] }}{% endif %}
{%- endmacro %}
{# Prints given deps #}
{%- macro dependencies(deps) %}
{%- for dep in deps -%}
{{ one_dep(dep) }}
{%- endfor %}
{%- endmacro %}
%define sname {{ data.name }}
%define version {{ data.version }}
%define release 1
%global python /usr/bin/python27

Summary:    {{ data.summary }}
Name:       python27-%{sname}
Version:    %{version}
Release:    %{release}%{?dist}
License:    {{ data.license|truncate(80)|wordwrap }}
URL:        {{ data.home_page }}
Source0:    {{ data.url|replace(data.name, '%{sname}')|replace(data.version, '%{version}') }}
Group:      Development/Libraries
BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix:     %{_prefix}

{%- if not data.has_extension %}
BuildArch:      noarch
{%- endif %}
{{ dependencies(data.build_deps) }}
{{ dependencies(data.runtime_deps) }}
BuildRequires:  python27-env
BuildRequires:  python27-python-setuptools
Requires:   python27-env
BuildRequires:  devtoolset-2-gcc
BuildRequires:  devtoolset-2-binutils
Provides:   %{sname} = %{version}-%{release}

%description
{{ data.description|truncate(400)|wordwrap }}

%prep
%setup -n %{sname}-%{version}

%build
/usr/bin/scl enable devtoolset-2 python27 "CFLAGS=\"$RPM_OPT_FLAGS\" python setup.py build"

%install
/usr/bin/scl enable devtoolset-2 python27 "python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES"

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* {{ data.changelog_date_packager }} - {{ data.version }}-%{release}
- Initial package.
