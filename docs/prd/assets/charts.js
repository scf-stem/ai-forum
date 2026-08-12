// PRD 图表初始化
(function() {
  // 成本结构饼图
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  var chart = echarts.init(document.getElementById('chart-cost'), null, { renderer: 'svg' });
  chart.setOption({
    tooltip: { trigger: 'item', appendToBody: true, formatter: '{b}: {d}%' },
    legend: { bottom: 0, textStyle: { color: muted, fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 8, borderColor: bg2, borderWidth: 2 },
      label: { show: true, color: accent, fontSize: 12, formatter: '{b}\n{d}%' },
      labelLine: { length: 12, length2: 10 },
      data: [
        { value: 45, name: '大模型 Token 调用', itemStyle: { color: accent } },
        { value: 20, name: '联网搜索 API', itemStyle: { color: accent2 } },
        { value: 15, name: '向量检索 / Embedding', itemStyle: { color: '#06b6d4' } },
        { value: 15, name: '服务器 / 带宽托管', itemStyle: { color: '#f59e0b' } },
        { value: 5, name: '其他', itemStyle: { color: muted } }
      ]
    }]
  });
  window.addEventListener('resize', function () { chart.resize(); });
})();
