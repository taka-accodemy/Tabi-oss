cube(`Sales`, {
  sql: `SELECT * FROM sales`,
  
  dimensions: {
    id: {
      sql: `id`,
      type: `string`,
      primaryKey: true,
    },
    
    customerId: {
      sql: `customer_id`,
      type: `string`,
    },
    
    productId: {
      sql: `product_id`,
      type: `string`,
    },
    
    orderDate: {
      sql: `order_date`,
      type: `time`,
    },
    
    status: {
      sql: `status`,
      type: `string`,
    },
    
    region: {
      sql: `region`,
      type: `string`,
    },
    
    channel: {
      sql: `channel`,
      type: `string`,
    },
  },
  
  measures: {
    count: {
      type: `count`,
      drillMembers: [id, customerId, productId, orderDate],
    },
    
    totalAmount: {
      sql: `amount`,
      type: `sum`,
      format: `currency`,
    },
    
    averageAmount: {
      sql: `amount`,
      type: `avg`,
      format: `currency`,
    },
    
    totalQuantity: {
      sql: `quantity`,
      type: `sum`,
    },
    
    averageQuantity: {
      sql: `quantity`,
      type: `avg`,
    },
    
    uniqueCustomers: {
      sql: `customer_id`,
      type: `countDistinct`,
    },
    
    uniqueProducts: {
      sql: `product_id`,
      type: `countDistinct`,
    },
  },
  
  joins: {
    Customers: {
      sql: `${CUBE}.customer_id = ${Customers}.id`,
      relationship: `belongsTo`,
    },
    
    Products: {
      sql: `${CUBE}.product_id = ${Products}.id`,
      relationship: `belongsTo`,
    },
  },
  
  preAggregations: {
    main: {
      measures: [totalAmount, count],
      dimensions: [orderDate],
      timeDimension: orderDate,
      granularity: `day`,
      refreshKey: {
        every: `1 hour`,
      },
    },
    
    byCustomer: {
      measures: [totalAmount, count],
      dimensions: [customerId],
      refreshKey: {
        every: `1 hour`,
      },
    },
    
    byProduct: {
      measures: [totalAmount, count],
      dimensions: [productId],
      refreshKey: {
        every: `1 hour`,
      },
    },
  },
});