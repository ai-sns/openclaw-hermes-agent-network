import pkg_resources

def get_installed_packages():
    """
    获取当前环境中安装的所有 Python 包及其版本信息。
    :return: 一个包含包名和版本的列表
    """
    # 获取当前环境中已安装的所有分发包
    installed_packages = pkg_resources.working_set
    
    # 构建包名和版本的字典
    package_list = {pkg.project_name: pkg.version for pkg in installed_packages}
    
    return package_list

if __name__ == "__main__":
    # 输出已安装的包及其版本
    installed_packages = get_installed_packages()
    for package, version in installed_packages.items():
        print(f"{package}=={version}")