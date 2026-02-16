cube(`Customers`, {
  sql: `SELECT * FROM customers`,
  
  dimensions: {
    id: {
      sql: `id`,
      type: `string`,
      primaryKey: true,
    },
    
    name: {
      sql: `name`,
      type: `string`,
    },
    
    email: {
      sql: `email`,
      type: `string`,
    },
    
    phone: {
      sql: `phone`,
      type: `string`,
    },
    
    address: {
      sql: `address`,
      type: `string`,
    },
    
    city: {
      sql: `city`,
      type: `string`,
    },
    
    state: {
      sql: `state`,
      type: `string`,
    },
    
    country: {
      sql: `country`,
      type: `string`,
    },
    
    postalCode: {
      sql: `postal_code`,
      type: `string`,
    },
    
    segment: {
      sql: `segment`,
      type: `string`,
    },
    
    registrationDate: {
      sql: `registration_date`,
      type: `time`,
    },
    
    lastPurchaseDate: {
      sql: `last_purchase_date`,
      type: `time`,
    },
  },
  
  measures: {
    count: {
      type: `count`,
      drillMembers: [id, name, email, city, country],
    },
    
    totalSpent: {
      sql: `${Sales.totalAmount}`,
      type: `sum`,
      format: `currency`,
    },
    
    averageSpent: {
      sql: `${Sales.totalAmount}`,
      type: `avg`,
      format: `currency`,
    },
    
    orderCount: {
      sql: `${Sales.count}`,
      type: `sum`,
    },
    
    averageOrderValue: {
      sql: `${Sales.averageAmount}`,
      type: `avg`,
      format: `currency`,
    },
    
    uniqueProductsPurchased: {
      sql: `${Sales.uniqueProducts}`,
      type: `sum`,
    },
    
    daysSinceLastPurchase: {
      sql: `CURRENT_DATE - last_purchase_date`,
      type: `avg`,
    },
    
    lifetimeValue: {
      sql: `${Sales.totalAmount}`,
      type: `sum`,
      format: `currency`,
    },
  },
  
  joins: {
    Sales: {
      sql: `${CUBE}.id = ${Sales}.customer_id`,
      relationship: `hasMany`,
    },
  },
  
  segments: {
    highValue: {
      sql: `${totalSpent} > 1000`,
    },
    
    active: {
      sql: `${daysSinceLastPurchase} <= 30`,
    },
    
    newCustomer: {
      sql: `${orderCount} = 1`,
    },
    
    loyalCustomer: {
      sql: `${orderCount} >= 5`,
    },
  },
  
  preAggregations: {
    main: {
      measures: [count, totalSpent, orderCount],
      dimensions: [segment, country, city],
      refreshKey: {
        every: `1 hour`,
      },
    },
    
    customerSummary: {
      measures: [totalSpent, orderCount, averageOrderValue],
      dimensions: [id, name],
      refreshKey: {
        every: `1 hour`,
      },
    },
  },
});