import { expect, test } from '@playwright/test';

const warehouses=[{id:'w-a',name:'一号仓',code:'A'},{id:'w-b',name:'二号仓',code:'B'}];
const zones=[{id:'z-chilled',warehouse_id:'w-a',code:'冷藏间 A',setpoint_decic:40},
  {id:'z-frozen',warehouse_id:'w-a',code:'冷冻间 A',setpoint_decic:-180}];

test.beforeEach(async ({page})=>{
  await page.addInitScript(()=>localStorage.setItem('dsh_token','dev-operator-token'));
});

test('真实仓库和所属温区加载后才能创建本地入库任务',async ({page})=>{
  await page.goto('/#/warehouseOps');
  await page.getByRole('button',{name:'入库作业',exact:true}).click();
  const warehouse=page.getByLabel('入库仓库'),zone=page.getByLabel('入库温区');
  await expect(warehouse).not.toHaveValue('');
  await expect(zone).not.toHaveValue('');
  const current=await warehouse.inputValue();
  const response=await page.request.get(`/api/v1/warehouses/${current}/zones?limit=100`,{headers:{Authorization:'Bearer dev-operator-token'}});
  expect(response.ok()).toBeTruthy();
  const available=(await response.json()).items;
  expect(available.map((z:{id:string})=>z.id)).toContain(await zone.inputValue());
  await expect(page.getByRole('button',{name:'创建入库任务',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'创建入库任务',exact:true}).click();
  await expect(page.getByText('IN-001',{exact:true})).toBeVisible();
});

test('切换仓库清除旧温区，无温区时禁用提交，读取失败可刷新恢复',async ({page})=>{
  let fail=false;
  await page.route('**/api/v1/warehouses?*',r=>r.fulfill({json:{items:warehouses}}));
  await page.route('**/api/v1/warehouses/*/zones?*',r=>{
    const second=r.request().url().includes('/w-b/');
    if(second && fail)return r.fulfill({status:503,json:{code:'dependency_unavailable',message:'test unavailable'}});
    return r.fulfill({json:{items:second?[]:[...zones,{id:'foreign',warehouse_id:'w-b',code:'其他仓库',setpoint_decic:30}]}});
  });
  await page.goto('/#/warehouseOps');
  await page.getByRole('button',{name:'入库作业',exact:true}).click();
  const warehouse=page.getByLabel('入库仓库'),zone=page.getByLabel('入库温区'),create=page.getByRole('button',{name:'创建入库任务',exact:true});
  await expect(zone).toHaveValue('z-chilled');
  await expect(zone.locator('option')).toHaveCount(3);
  await zone.selectOption('z-frozen');
  await create.click();
  await expect(page.getByRole('cell',{name:'冷冻间 A（-18°C）',exact:true})).toBeVisible();
  await warehouse.selectOption('w-b');
  await expect(zone).toBeDisabled();await expect(zone).toHaveValue('');await expect(create).toBeDisabled();
  await expect(page.getByText('所选仓库暂无温区，请先配置温区后再创建入库任务。')).toBeVisible();
  await warehouse.selectOption('w-a');await expect(zone).toHaveValue('z-chilled');
  fail=true;await warehouse.selectOption('w-b');
  await expect(page.getByRole('alert')).toContainText('温区读取失败');await expect(create).toBeDisabled();
  fail=false;await page.getByRole('button',{name:'刷新仓库与温区',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);await expect(create).toBeDisabled();
});

test('没有仓库时显示提示，不能用写死仓库编号创建任务',async ({page})=>{
  await page.route('**/api/v1/warehouses?*',r=>r.fulfill({json:{items:[]}}));
  await page.goto('/#/warehouseOps');await page.getByRole('button',{name:'入库作业',exact:true}).click();
  await expect(page.getByText('暂无可选仓库，请先导入仓库主数据。')).toBeVisible();
  await expect(page.getByLabel('入库仓库')).toBeDisabled();
  await expect(page.getByLabel('入库温区')).toBeDisabled();
  await expect(page.getByRole('button',{name:'创建入库任务',exact:true})).toBeDisabled();
});

test('快速切换仓库时忽略迟到的旧温区响应',async ({page})=>{
  let release:()=>void=()=>{};
  const hold=new Promise<void>(resolve=>{release=resolve;});
  let entered:()=>void=()=>{};
  const pending=new Promise<void>(resolve=>{entered=resolve;});
  await page.route('**/api/v1/warehouses?*',r=>r.fulfill({json:{items:warehouses}}));
  await page.route('**/api/v1/warehouses/*/zones?*',async r=>{
    if(r.request().url().includes('/w-a/')){entered();await hold;await r.fulfill({json:{items:zones}});}
    else await r.fulfill({json:{items:[{id:'z-b',warehouse_id:'w-b',code:'二号仓冷藏间',setpoint_decic:50}]}});
  });
  await page.goto('/#/warehouseOps');await page.getByRole('button',{name:'入库作业',exact:true}).click();
  await pending;
  await page.getByLabel('入库仓库').selectOption('w-b');
  await expect(page.getByLabel('入库温区')).toHaveValue('z-b');
  const oldResponse=page.waitForResponse(r=>r.url().includes('/w-a/zones'));
  release();await oldResponse;
  await expect(page.getByLabel('入库温区')).toHaveValue('z-b');
  await expect(page.getByLabel('入库温区').locator('option')).toHaveCount(2);
});
