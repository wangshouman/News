function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {
    $(".release_form").submit(function (e) {
        e.preventDefault()
        $('#rich_content').val(tinyMCE.get('rich_content').getContent());
        // 发布新闻
        $(this).ajaxSubmit({
            url: "/user/news_release",
            type: "POST",
            headers: {
                "X-CSRFToken": getCookie('csrf_token')
            },
            success: function (resp) {
                if (resp.errno == "0") {
                    // 选中索引为6的左边单菜单
                    window.parent.fnChangeMenu(6)
                    // 滚动到顶部
                    window.parent.scrollTo(0, 0)
                } else {
                    alert(resp.errmsg)
                }
            }
        })
    })
})