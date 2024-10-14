// 获取所有具有 'imgcls' 类名的图片元素，并将其转换为数组-1
var images = Array.from(document.getElementsByClassName('imgcls'));

// 遍历每个图片元素并隐藏它们
images.forEach(function(image) {
    image.style.display = 'none'; // 将图片元素的显示样式设置为 'none'
});
